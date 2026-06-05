from datetime import datetime
from decimal import Decimal

from app.core.datetime_utils import to_app_tz, utc_now
from app.core.logging import get_logger
from app.exceptions.queue_snapshot_exceptions import QueueSnapshotNotFoundError
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.queue_reports import QueueReport, ReportStatusEnum
from app.models.queue_snapshot import QueueSnapshot, SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum, Restaurant
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.meal_period_service import MealPeriodService
from app.services.websocket_service import SnapshotWebSocketService

logger = get_logger(__name__)

STATUS_MAP_VALUE = {
    ReportStatusEnum.NO_QUEUE: 0,
    ReportStatusEnum.SMALL: 1,
    ReportStatusEnum.MEDIUM: 2,
    ReportStatusEnum.LARGE: 3,
}

_VALUE_STATUS_MAP = {
    0: SnapshotStatusEnum.NO_QUEUE,
    1: SnapshotStatusEnum.SMALL,
    2: SnapshotStatusEnum.MEDIUM,
    3: SnapshotStatusEnum.LARGE,
}

_FOOD_ENDED_QUORUM = 3
_FOOD_ENDED_WINDOW_SECONDS = 5 * 60

_REPORT_WINDOW_MINUTES = 15

_ADAPTIVE_5MIN_MIN_COUNT = 5
_ADAPTIVE_10MIN_MIN_COUNT = 3

_WEIGHT_UNDER_1MIN = 0.95
_WEIGHT_UNDER_5MIN = 0.70
_WEIGHT_UNDER_10MIN = 0.40
_WEIGHT_OVER_10MIN = 0.15

_CONFIDENCE_PRECISION = Decimal("0.01")


class SnapshotStatusService:
    def __init__(
        self,
        snapshot_repo: QueueSnapshotRepository,
        report_repo: QueueReportRepository,
        restaurant_repo: RestaurantRepository,
        meal_period_service: MealPeriodService,
    ):
        self.snapshot_repo = snapshot_repo
        self.report_repo = report_repo
        self.restaurant_repo = restaurant_repo
        self.meal_period_service = meal_period_service

    async def _get_restaurant_by_id_or_error(self, ru_id: int) -> Restaurant:
        restaurant = await self.restaurant_repo.get_by_id(ru_id)
        if not restaurant:
            logger.warning("Restaurante não encontrado: %s", ru_id)
            raise RestaurantNotFoundError()
        return restaurant

    def _get_adaptive_time_window(
        self, recent_reports: list[QueueReport], now: datetime
    ) -> int:
        count_5_min = sum(
            1 for r in recent_reports if (now - r.created_at).total_seconds() <= 5 * 60
        )
        count_10_min = sum(
            1 for r in recent_reports if (now - r.created_at).total_seconds() <= 10 * 60
        )

        if count_5_min >= _ADAPTIVE_5MIN_MIN_COUNT:
            return 5
        elif count_10_min >= _ADAPTIVE_10MIN_MIN_COUNT:
            return 10
        else:
            return _REPORT_WINDOW_MINUTES

    def _get_temporal_weight(self, seconds_ago: float) -> float:
        if seconds_ago <= 60:
            return _WEIGHT_UNDER_1MIN
        elif seconds_ago <= 5 * 60:
            return _WEIGHT_UNDER_5MIN
        elif seconds_ago <= 10 * 60:
            return _WEIGHT_UNDER_10MIN
        else:
            return _WEIGHT_OVER_10MIN

    async def _resolve_context(
        self, ru_id: int
    ) -> tuple[Restaurant, MealPeriodEnum, list[QueueReport]]:
        """Resolve restaurant, meal_period e relatos dos últimos 15min (3 queries)."""
        restaurant = await self._get_restaurant_by_id_or_error(ru_id)
        dt = to_app_tz(utc_now())
        meal_period = await self.meal_period_service.resolve(ru_id=restaurant.id, at=dt)
        recent_reports = await self.report_repo.list_recent_by_period_within_minutes(
            ru_id=restaurant.id,
            meal_period=meal_period,
            minutes=_REPORT_WINDOW_MINUTES,
        )
        return restaurant, meal_period, recent_reports

    def _compute_status(
        self, recent_reports: list[QueueReport]
    ) -> tuple[SnapshotStatusEnum, Decimal, Decimal | None]:
        """Retorna (status, avg_confidence, avg_status_value). Sem IO.

        avg_status_value é o valor contínuo ponderado antes do arredondamento inteiro
        que determina o status. None nos paths NO_DATA e FOOD_ENDED.
        """
        if not recent_reports:
            return SnapshotStatusEnum.NO_DATA, Decimal("1.00"), None

        now = utc_now()

        # FOOD_ENDED quorum: ≥3 relatos nos últimos 5min sobrescreve qualquer cálculo
        food_ended_5min = [
            r
            for r in recent_reports
            if r.status == ReportStatusEnum.FOOD_ENDED
            and (now - r.created_at).total_seconds() <= _FOOD_ENDED_WINDOW_SECONDS
        ]
        if len(food_ended_5min) >= _FOOD_ENDED_QUORUM:
            avg_conf = (
                sum(r.confidence_score for r in food_ended_5min)
                / Decimal(len(food_ended_5min))
            ).quantize(_CONFIDENCE_PRECISION)
            return SnapshotStatusEnum.FOOD_ENDED, avg_conf, None

        adaptive_window = self._get_adaptive_time_window(recent_reports, now)

        window_reports = [
            r
            for r in recent_reports
            if (now - r.created_at).total_seconds() <= adaptive_window * 60
        ]

        scorable_reports = [r for r in window_reports if r.status in STATUS_MAP_VALUE]

        if not scorable_reports:
            return SnapshotStatusEnum.NO_DATA, Decimal("1.00"), None

        total_weighted_value = 0.0
        total_weight = 0.0
        total_temporal_weight = 0.0

        for report in scorable_reports:
            seconds_ago = (now - report.created_at).total_seconds()
            temporal_weight = self._get_temporal_weight(seconds_ago)
            final_weight = temporal_weight * float(report.confidence_score)
            status_value = STATUS_MAP_VALUE[report.status]
            total_weighted_value += status_value * final_weight
            total_weight += final_weight
            total_temporal_weight += temporal_weight

        if total_weight == 0:
            return SnapshotStatusEnum.NO_DATA, Decimal("1.00"), None

        rounded_value = round(total_weighted_value / total_weight)
        avg_status_value = Decimal(str(total_weighted_value / total_weight)).quantize(
            _CONFIDENCE_PRECISION
        )

        raw_confidence = total_weight / total_temporal_weight
        avg_confidence = Decimal(str(round(raw_confidence, 2))).quantize(
            _CONFIDENCE_PRECISION
        )

        return _VALUE_STATUS_MAP[rounded_value], avg_confidence, avg_status_value

    async def calculate_snapshot_status(self, ru_id: int) -> SnapshotStatusEnum:
        _, _, recent_reports = await self._resolve_context(ru_id)
        status, _, _ = self._compute_status(recent_reports)
        logger.debug("ru_id=%s status calculado: %s", ru_id, status.value)
        return status

    async def update_snapshot(self, ru_id: int) -> QueueSnapshot:
        restaurant, meal_period, recent_reports = await self._resolve_context(ru_id)

        new_status, new_confidence, new_avg_status_value = self._compute_status(
            recent_reports
        )

        snapshot = await self.snapshot_repo.get_by_ru_id_and_meal_period(
            ru_id=restaurant.id, meal_period=meal_period
        )
        if not snapshot:
            logger.warning(
                "Snapshot não encontrado: ru_id=%s meal_period=%s",
                restaurant.id,
                meal_period.value,
            )
            raise QueueSnapshotNotFoundError()

        snapshot.current_status = new_status
        snapshot.avg_status_value = new_avg_status_value
        snapshot.reports_last_15m = len(recent_reports)
        snapshot.last_report_at = (
            recent_reports[0].created_at if recent_reports else None
        )
        snapshot.confidence_score = new_confidence

        await self.snapshot_repo.db_session.commit()

        logger.debug(
            "ru_id=%s snapshot atualizado: status=%s reports_last_15m=%d",
            restaurant.id,
            new_status.value,
            len(recent_reports),
        )

        await SnapshotWebSocketService.publish_snapshot(
            snapshot=snapshot,
            restaurant_public_id=restaurant.public_id,
        )

        return snapshot
