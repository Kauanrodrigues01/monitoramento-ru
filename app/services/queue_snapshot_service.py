from uuid import UUID

from app.core.datetime_utils import to_app_tz, utc_now
from app.core.logging import get_logger
from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.exceptions.queue_snapshot_exceptions import (
    QueueSnapshotBulkLimitExceededError,
    QueueSnapshotNotFoundError,
)
from app.models.restaurant import MealPeriodEnum, Restaurant
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.queue_snapshot_schemas import (
    QueueSnapshotBulkItem,
    QueueSnapshotResponse,
)
from app.services._mixins import RestaurantResolverMixin
from app.services.meal_period_service import MealPeriodService

logger = get_logger(__name__)

BULK_LIMIT = 10


class QueueSnapshotService(RestaurantResolverMixin):
    def __init__(
        self,
        repo: QueueSnapshotRepository,
        restaurant_repo: RestaurantRepository,
        meal_period_service: MealPeriodService,
    ):
        self.repo = repo
        self.restaurant_repo = restaurant_repo
        self.meal_period_service = meal_period_service

    async def get_status(self, restaurant_public_id: UUID) -> QueueSnapshotResponse:
        restaurant = await self._get_restaurant_by_public_id_or_error(
            restaurant_public_id
        )

        dt = to_app_tz(utc_now())

        meal_period = await self.meal_period_service.resolve(ru_id=restaurant.id, at=dt)

        snapshot = await self.repo.get_by_ru_id_and_meal_period(
            ru_id=restaurant.id, meal_period=meal_period
        )

        if not snapshot:
            logger.warning(
                "Snapshot não encontrado: ru_id=%s, meal_period=%s",
                restaurant.id,
                meal_period.value,
            )
            raise QueueSnapshotNotFoundError()

        freshness_min: int | None = None
        if snapshot.last_report_at is not None:
            freshness_min = max(
                0,
                round((utc_now() - snapshot.last_report_at).total_seconds() / 60),
            )

        return QueueSnapshotResponse(
            meal_period=snapshot.meal_period,
            current_status=snapshot.current_status,
            reports_last_15m=snapshot.reports_last_15m,
            last_report_at=snapshot.last_report_at,
            updated_at=snapshot.updated_at,
            confidence_score=snapshot.confidence_score,
            data_freshness_minutes=freshness_min,
        )

    async def get_bulk_status(
        self, public_ids: list[UUID]
    ) -> list[QueueSnapshotBulkItem]:
        if len(public_ids) > BULK_LIMIT:
            logger.warning(
                "Limite de bulk excedido: %d IDs solicitados (máximo %d)",
                len(public_ids),
                BULK_LIMIT,
            )
            raise QueueSnapshotBulkLimitExceededError()

        restaurants = await self.restaurant_repo.get_bulk_by_public_ids(public_ids)
        if not restaurants:
            logger.warning(
                "Bulk status: nenhum restaurante ativo encontrado para os %d IDs informados",
                len(public_ids),
            )
            return []

        dt = to_app_tz(utc_now())

        # resolve meal_period por restaurante; pula fechados/fora de horário
        period_groups: dict[MealPeriodEnum, list[Restaurant]] = {}
        for restaurant in restaurants:
            try:
                period = await self.meal_period_service.resolve(
                    ru_id=restaurant.id, at=dt
                )
                period_groups.setdefault(period, []).append(restaurant)
            except (
                RestaurantClosedAllDayError,
                OutsideMealHoursError,
                MealPeriodClosedError,
            ):
                logger.debug(
                    "Bulk status: ru_id=%s ignorado — fora do horário de funcionamento",
                    restaurant.id,
                )
                continue

        if not period_groups:
            return []

        results: list[QueueSnapshotBulkItem] = []
        for meal_period, group in period_groups.items():
            ru_map = {r.id: r for r in group}
            snapshots = await self.repo.get_bulk_by_ru_ids_and_meal_period(
                list(ru_map.keys()), meal_period
            )
            for snapshot in snapshots:
                restaurant = ru_map[snapshot.ru_id]
                results.append(
                    QueueSnapshotBulkItem(
                        restaurant_public_id=restaurant.public_id,
                        meal_period=snapshot.meal_period,
                        current_status=snapshot.current_status,
                        reports_last_15m=snapshot.reports_last_15m,
                        last_report_at=snapshot.last_report_at,
                        updated_at=snapshot.updated_at,
                        confidence_score=snapshot.confidence_score,
                    )
                )

        return results
