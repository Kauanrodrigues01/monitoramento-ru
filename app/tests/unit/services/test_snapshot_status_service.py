from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from freezegun import freeze_time

from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.exceptions.queue_snapshot_exceptions import QueueSnapshotNotFoundError
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.queue_reports import ReportStatusEnum
from app.models.queue_snapshot import QueueSnapshot, SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.meal_period_service import MealPeriodService
from app.services.snapshot_status_service import SnapshotStatusService
from app.tests.factories.models.unit.queue_report_model_factory import (
    QueueReportFactory,
)
from app.tests.factories.models.unit.queue_snapshot_model_factory import (
    QueueSnapshotFactory,
)
from app.tests.factories.models.unit.restaurant_model_factory import RestaurantFactory

_NOW = datetime(2026, 5, 27, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_snapshot_repo():
    repo = AsyncMock(spec=QueueSnapshotRepository)
    repo.db_session = AsyncMock()
    return repo


@pytest.fixture
def mock_report_repo():
    return AsyncMock(spec=QueueReportRepository)


@pytest.fixture
def mock_restaurant_repo():
    return AsyncMock(spec=RestaurantRepository)


@pytest.fixture
def mock_meal_period_service():
    return AsyncMock(spec=MealPeriodService)


@pytest.fixture
def service(
    mock_snapshot_repo,
    mock_report_repo,
    mock_restaurant_repo,
    mock_meal_period_service,
):
    return SnapshotStatusService(
        snapshot_repo=mock_snapshot_repo,
        report_repo=mock_report_repo,
        restaurant_repo=mock_restaurant_repo,
        meal_period_service=mock_meal_period_service,
    )


# ── TestGetAdaptiveTimeWindow ─────────────────────────────────────────────────


class TestGetAdaptiveTimeWindow:
    def test_returns_5_when_5_or_more_reports_in_last_5min(self, service):
        reports = [
            QueueReportFactory.build(created_at=_NOW - timedelta(seconds=i * 30))
            for i in range(1, 6)
        ]
        assert service._get_adaptive_time_window(reports, _NOW) == 5

    def test_returns_5_at_boundary_of_exactly_5_reports_in_5min(self, service):
        reports = [
            QueueReportFactory.build(created_at=_NOW - timedelta(seconds=300))
            for _ in range(5)
        ]  # exactly 5 * 60s
        assert service._get_adaptive_time_window(reports, _NOW) == 5

    def test_returns_10_when_3_reports_in_10min_but_fewer_than_5_in_5min(self, service):
        reports = [
            QueueReportFactory.build(created_at=_NOW - timedelta(seconds=60)),
            QueueReportFactory.build(created_at=_NOW - timedelta(seconds=120)),
            QueueReportFactory.build(
                created_at=_NOW - timedelta(seconds=360)
            ),  # 6 min — within 10min, not 5min
        ]
        assert service._get_adaptive_time_window(reports, _NOW) == 10

    def test_returns_10_at_boundary_of_exactly_3_reports_in_10min(self, service):
        reports = [
            QueueReportFactory.build(created_at=_NOW - timedelta(seconds=600))
            for _ in range(3)
        ]  # exactly 10 * 60s
        assert service._get_adaptive_time_window(reports, _NOW) == 10

    def test_returns_15_when_fewer_than_3_reports_in_last_10min(self, service):
        reports = [
            QueueReportFactory.build(created_at=_NOW - timedelta(seconds=360)),
            QueueReportFactory.build(created_at=_NOW - timedelta(seconds=540)),
        ]
        assert service._get_adaptive_time_window(reports, _NOW) == 15

    def test_5min_window_takes_priority_when_both_thresholds_met(self, service):
        # 5 in 5min (triggers 5-min branch) + 3 in 10min (would trigger 10-min branch)
        reports = [
            QueueReportFactory.build(created_at=_NOW - timedelta(seconds=i * 30))
            for i in range(1, 6)
        ]
        assert service._get_adaptive_time_window(reports, _NOW) == 5

    def test_returns_15_when_no_reports(self, service):
        assert service._get_adaptive_time_window([], _NOW) == 15


# ── TestGetTemporalWeight ─────────────────────────────────────────────────────


class TestGetTemporalWeight:
    def test_returns_095_under_60s(self, service):
        assert service._get_temporal_weight(30) == 0.95

    def test_returns_095_at_exactly_60s(self, service):
        assert service._get_temporal_weight(60) == 0.95

    def test_returns_070_just_after_60s(self, service):
        assert service._get_temporal_weight(61) == 0.70

    def test_returns_070_at_exactly_5min(self, service):
        assert service._get_temporal_weight(5 * 60) == 0.70

    def test_returns_040_just_after_5min(self, service):
        assert service._get_temporal_weight(5 * 60 + 1) == 0.40

    def test_returns_040_at_exactly_10min(self, service):
        assert service._get_temporal_weight(10 * 60) == 0.40

    def test_returns_015_just_after_10min(self, service):
        assert service._get_temporal_weight(10 * 60 + 1) == 0.15

    def test_returns_015_for_very_old_report(self, service):
        assert service._get_temporal_weight(30 * 60) == 0.15


# ── TestComputeStatus ─────────────────────────────────────────────────────────


class TestComputeStatus:
    @freeze_time(_NOW)
    def test_empty_reports_returns_no_data_with_full_confidence(self, service):
        status, conf, _ = service._compute_status([])
        assert status == SnapshotStatusEnum.NO_DATA
        assert conf == Decimal("1.00")

    @freeze_time(_NOW)
    def test_food_ended_quorum_exactly_3_in_5min_returns_food_ended(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=60),
            )
            for _ in range(3)
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.FOOD_ENDED

    @freeze_time(_NOW)
    def test_food_ended_quorum_more_than_3_in_5min_returns_food_ended(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=60),
            )
            for _ in range(5)
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.FOOD_ENDED

    @freeze_time(_NOW)
    def test_food_ended_quorum_requires_at_least_3_reports(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=60),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=120),
            ),
        ]
        status, _, _ = service._compute_status(reports)
        assert status != SnapshotStatusEnum.FOOD_ENDED

    @freeze_time(_NOW)
    def test_food_ended_count_only_includes_reports_within_last_5min(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=60),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=400),
            ),  # > 5min
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=500),
            ),  # > 5min
        ]
        status, _, _ = service._compute_status(reports)
        assert status != SnapshotStatusEnum.FOOD_ENDED

    @freeze_time(_NOW)
    def test_food_ended_at_exactly_5min_boundary_counts_for_quorum(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=300),
            )
            for _ in range(3)
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.FOOD_ENDED

    @freeze_time(_NOW)
    def test_food_ended_confidence_is_simple_average_of_quorum_reports(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=60),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                confidence_score=Decimal("0.50"),
                created_at=_NOW - timedelta(seconds=60),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                confidence_score=Decimal("0.50"),
                created_at=_NOW - timedelta(seconds=60),
            ),
        ]
        _, conf, _ = service._compute_status(reports)
        # (1.00 + 0.50 + 0.50) / 3 = 0.6666... → 0.67
        assert conf == Decimal("0.67")

    @freeze_time(_NOW)
    def test_only_food_ended_without_quorum_returns_no_data(self, service):
        # 2 FOOD_ENDED (sem quórum) → não há scorable_reports → NO_DATA
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=60),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=120),
            ),
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.NO_DATA

    @freeze_time(_NOW)
    def test_no_queue_reports_return_no_queue_status(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.NO_QUEUE,
                created_at=_NOW - timedelta(seconds=30),
            )
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.NO_QUEUE

    @freeze_time(_NOW)
    def test_small_reports_return_small_status(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL, created_at=_NOW - timedelta(seconds=30)
            )
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.SMALL

    @freeze_time(_NOW)
    def test_medium_reports_return_medium_status(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.MEDIUM, created_at=_NOW - timedelta(seconds=30)
            )
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.MEDIUM

    @freeze_time(_NOW)
    def test_large_reports_return_large_status(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.LARGE, created_at=_NOW - timedelta(seconds=30)
            )
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.LARGE

    @freeze_time(_NOW)
    def test_weighted_average_of_small_and_large_returns_medium(self, service):
        # SMALL(1) + LARGE(3) com mesmo peso → (1+3)/2 = 2.0 → MEDIUM
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL, created_at=_NOW - timedelta(seconds=30)
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.LARGE, created_at=_NOW - timedelta(seconds=30)
            ),
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.MEDIUM

    @freeze_time(_NOW)
    def test_weighted_average_rounds_correctly_toward_large(self, service):
        # 1 MEDIUM(2) + 2 LARGE(3) com mesmo peso → (2+3+3)/3 = 2.67 → round = 3 → LARGE
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.MEDIUM, created_at=_NOW - timedelta(seconds=30)
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.LARGE, created_at=_NOW - timedelta(seconds=30)
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.LARGE, created_at=_NOW - timedelta(seconds=30)
            ),
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.LARGE

    @freeze_time(_NOW)
    def test_food_ended_excluded_from_weighted_calculation(self, service):
        # 1 LARGE + 1 FOOD_ENDED (não scorable) → LARGE, não MEDIUM
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.LARGE, created_at=_NOW - timedelta(seconds=30)
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=30),
            ),
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.LARGE

    @freeze_time(_NOW)
    def test_reports_outside_adaptive_window_excluded_from_calculation(self, service):
        # 5 NO_QUEUE em 5min → janela adaptativa = 5min
        # 1 LARGE a 8min → excluído do cálculo
        reports = [
            *[
                QueueReportFactory.build(
                    status=ReportStatusEnum.NO_QUEUE,
                    created_at=_NOW - timedelta(seconds=i * 30),
                )
                for i in range(1, 6)
            ],
            QueueReportFactory.build(
                status=ReportStatusEnum.LARGE, created_at=_NOW - timedelta(seconds=480)
            ),
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.NO_QUEUE

    @freeze_time(_NOW)
    def test_reports_outside_10min_adaptive_window_excluded_from_calculation(
        self, service
    ):
        # 3 NO_QUEUE entre 6-9min → count_5min=0, count_10min=3 → janela = 10min
        # 1 LARGE a 12min → fora da janela de 10min, excluído
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.NO_QUEUE,
                created_at=_NOW - timedelta(seconds=360),
            ),  # 6min
            QueueReportFactory.build(
                status=ReportStatusEnum.NO_QUEUE,
                created_at=_NOW - timedelta(seconds=480),
            ),  # 8min
            QueueReportFactory.build(
                status=ReportStatusEnum.NO_QUEUE,
                created_at=_NOW - timedelta(seconds=540),
            ),  # 9min
            QueueReportFactory.build(
                status=ReportStatusEnum.LARGE, created_at=_NOW - timedelta(seconds=720)
            ),  # 12min
        ]
        status, _, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.NO_QUEUE

    @freeze_time(_NOW)
    def test_confidence_for_single_report_equals_its_own_confidence_score(
        self, service
    ):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("0.50"),
                created_at=_NOW - timedelta(seconds=30),
            )
        ]
        _, conf, _ = service._compute_status(reports)
        # avg = (0.95 * 0.50) / 0.95 = 0.50
        assert conf == Decimal("0.50")

    @freeze_time(_NOW)
    def test_confidence_is_temporally_weighted_average_of_reports(self, service):
        # Report A: confidence=1.00, seconds_ago=30 → temporal_weight=0.95
        # Report B: confidence=0.50, seconds_ago=200 → temporal_weight=0.70
        # total_weight = 0.95*1.00 + 0.70*0.50 = 1.30
        # total_temporal_weight = 0.95 + 0.70 = 1.65
        # avg_confidence = 1.30 / 1.65 ≈ 0.7878 → 0.79
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=30),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("0.50"),
                created_at=_NOW - timedelta(seconds=200),
            ),
        ]
        _, conf, _ = service._compute_status(reports)
        assert conf == Decimal("0.79")

    @freeze_time(_NOW)
    def test_no_data_path_returns_confidence_1_00(self, service):
        # Sem scorable (só FOOD_ENDED sem quórum) → NO_DATA → confidence padrão 1.00
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=60),
            )
        ]
        _, conf, _ = service._compute_status(reports)
        assert conf == Decimal("1.00")

    @freeze_time(_NOW)
    def test_returns_no_data_when_all_scorable_reports_have_zero_confidence(
        self, service
    ):
        # confidence_score=0 → final_weight=0 para todos → total_weight=0 → NO_DATA
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("0.00"),
                created_at=_NOW - timedelta(seconds=30),
            )
        ]
        status, conf, _ = service._compute_status(reports)
        assert status == SnapshotStatusEnum.NO_DATA
        assert conf == Decimal("1.00")

    # avg_status_value

    @freeze_time(_NOW)
    def test_avg_status_value_is_none_when_no_reports(self, service):
        _, _, avg = service._compute_status([])
        assert avg is None

    @freeze_time(_NOW)
    def test_avg_status_value_is_none_on_food_ended_path(self, service):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=60),
            )
            for _ in range(3)
        ]
        _, _, avg = service._compute_status(reports)
        assert avg is None

    @freeze_time(_NOW)
    def test_avg_status_value_is_none_when_no_scorable_reports(self, service):
        # Apenas FOOD_ENDED sem quorum → NO_DATA path
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.FOOD_ENDED,
                created_at=_NOW - timedelta(seconds=60),
            )
        ]
        _, _, avg = service._compute_status(reports)
        assert avg is None

    @freeze_time(_NOW)
    def test_avg_status_value_equals_status_value_for_single_report(self, service):
        # Único relato SMALL (valor=1) → avg_status_value deve ser 1.00
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL, created_at=_NOW - timedelta(seconds=30)
            )
        ]
        _, _, avg = service._compute_status(reports)
        assert avg == Decimal("1.00")

    @freeze_time(_NOW)
    def test_avg_status_value_is_continuous_before_integer_rounding(self, service):
        # 3 × SMALL(1) + 1 × MEDIUM(2) com pesos iguais → média = 1.25
        # round(1.25) = 1 → status=SMALL, mas avg_status_value deve ser 1.25 (contínuo)
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=30),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=30),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=30),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.MEDIUM,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=30),
            ),
        ]
        status, _, avg = service._compute_status(reports)
        assert status == SnapshotStatusEnum.SMALL
        assert avg is not None
        # valor contínuo deve estar entre SMALL(1) e MEDIUM(2)
        assert Decimal("1.00") < avg < Decimal("2.00")

    @freeze_time(_NOW)
    def test_avg_status_value_diverges_from_rounded_status(self, service):
        # SMALL(1) com peso 3 + MEDIUM(2) com peso 1 → média = (3+2)/4 = 1.25 → status=SMALL
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=30),  # peso 0.95
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=30),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=30),
            ),
            QueueReportFactory.build(
                status=ReportStatusEnum.MEDIUM,
                confidence_score=Decimal("1.00"),
                created_at=_NOW - timedelta(seconds=30),
            ),
        ]
        status, _, avg = service._compute_status(reports)
        assert status == SnapshotStatusEnum.SMALL
        # avg = (1+1+1+2)/4 = 1.25 → arredonda para 1 (SMALL), mas avg_status_value ≠ 1
        assert avg is not None
        assert avg < Decimal("2.00")  # valor contínuo menor que MEDIUM


# ── TestCalculateSnapshotStatus ───────────────────────────────────────────────


class TestCalculateSnapshotStatus:
    def _setup_context(
        self,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        ru_id: int = 1,
        meal_period: MealPeriodEnum = MealPeriodEnum.LUNCH,
        reports: list | None = None,
    ):
        restaurant = RestaurantFactory.build(id=ru_id)
        mock_restaurant_repo.get_by_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = meal_period
        mock_report_repo.list_recent_by_period_within_minutes.return_value = (
            reports or []
        )
        return restaurant

    async def test_returns_no_data_when_no_reports(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
    ):
        self._setup_context(
            mock_restaurant_repo, mock_meal_period_service, mock_report_repo
        )
        result = await service.calculate_snapshot_status(1)
        assert result == SnapshotStatusEnum.NO_DATA

    @freeze_time(_NOW)
    async def test_returns_computed_status_when_reports_present(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
    ):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.LARGE, created_at=_NOW - timedelta(seconds=30)
            )
        ]
        self._setup_context(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            reports=reports,
        )
        result = await service.calculate_snapshot_status(1)
        assert result == SnapshotStatusEnum.LARGE

    async def test_raises_restaurant_not_found_when_restaurant_is_missing(
        self, service, mock_restaurant_repo
    ):
        mock_restaurant_repo.get_by_id.return_value = None
        with pytest.raises(RestaurantNotFoundError):
            await service.calculate_snapshot_status(99)

    async def test_propagates_restaurant_closed_all_day_error(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.side_effect = RestaurantClosedAllDayError()
        with pytest.raises(RestaurantClosedAllDayError):
            await service.calculate_snapshot_status(1)

    async def test_propagates_outside_meal_hours_error(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()
        with pytest.raises(OutsideMealHoursError):
            await service.calculate_snapshot_status(1)

    async def test_propagates_meal_period_closed_error(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.side_effect = MealPeriodClosedError()
        with pytest.raises(MealPeriodClosedError):
            await service.calculate_snapshot_status(1)

    async def test_calls_report_repo_with_correct_ru_id_meal_period_and_window(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
    ):
        self._setup_context(
            mock_restaurant_repo, mock_meal_period_service, mock_report_repo, ru_id=7
        )
        await service.calculate_snapshot_status(7)
        mock_report_repo.list_recent_by_period_within_minutes.assert_called_once_with(
            ru_id=7, meal_period=MealPeriodEnum.LUNCH, minutes=15
        )

    async def test_calls_restaurant_repo_with_correct_ru_id(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
    ):
        self._setup_context(
            mock_restaurant_repo, mock_meal_period_service, mock_report_repo, ru_id=7
        )
        await service.calculate_snapshot_status(7)
        mock_restaurant_repo.get_by_id.assert_called_once_with(7)

    async def test_report_from_before_midnight_is_included_no_today_filter(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
    ):
        """Relato de 23:58 deve ser incluído quando calculado às 00:02 (sem filtro por data)."""
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.DINNER

        report_before_midnight = QueueReportFactory.build(status=ReportStatusEnum.LARGE)
        report_before_midnight.created_at = datetime(2026, 5, 26, 23, 58, 0, tzinfo=UTC)

        mock_report_repo.list_recent_by_period_within_minutes.return_value = [
            report_before_midnight
        ]

        with freeze_time(datetime(2026, 5, 27, 0, 2, 0, tzinfo=UTC)):
            result = await service.calculate_snapshot_status(1)

        assert result == SnapshotStatusEnum.LARGE


# ── TestUpdateSnapshot ────────────────────────────────────────────────────────


class TestUpdateSnapshot:
    @pytest.fixture(autouse=True)
    def mock_publish_snapshot(self):
        with patch(
            "app.services.snapshot_status_service.SnapshotWebSocketService.publish_snapshot",
            new_callable=AsyncMock,
        ) as mock:
            yield mock

    def _setup_happy_path(
        self,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
        ru_id: int = 1,
        meal_period: MealPeriodEnum = MealPeriodEnum.LUNCH,
        reports: list | None = None,
        snapshot: QueueSnapshot | None = None,
    ) -> tuple:
        restaurant = RestaurantFactory.build(id=ru_id)
        mock_restaurant_repo.get_by_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = meal_period
        mock_report_repo.list_recent_by_period_within_minutes.return_value = (
            reports or []
        )
        snap = snapshot or QueueSnapshotFactory.build(
            ru_id=ru_id, meal_period=meal_period
        )
        mock_snapshot_repo.get_by_ru_id_and_meal_period.return_value = snap
        return restaurant, snap

    @freeze_time(_NOW)
    async def test_updates_current_status_on_snapshot(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.LARGE, created_at=_NOW - timedelta(seconds=30)
            )
        ]
        _, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            reports=reports,
        )
        await service.update_snapshot(1)
        assert snap.current_status == SnapshotStatusEnum.LARGE

    async def test_updates_reports_last_15m_with_count_of_all_reports(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        reports = [QueueReportFactory.build() for _ in range(4)]
        _, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            reports=reports,
        )
        await service.update_snapshot(1)
        assert snap.reports_last_15m == 4

    @freeze_time(_NOW)
    async def test_updates_last_report_at_from_first_report_in_list(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        r1 = QueueReportFactory.build(created_at=_NOW - timedelta(seconds=30))
        r2 = QueueReportFactory.build(created_at=_NOW - timedelta(seconds=120))
        _, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            reports=[r1, r2],
        )
        await service.update_snapshot(1)
        assert snap.last_report_at == r1.created_at

    async def test_last_report_at_is_none_when_no_reports(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        _, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            reports=[],
        )
        await service.update_snapshot(1)
        assert snap.last_report_at is None

    @freeze_time(_NOW)
    async def test_updates_confidence_score_on_snapshot(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL,
                confidence_score=Decimal("0.50"),
                created_at=_NOW - timedelta(seconds=30),
            )
        ]
        _, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            reports=reports,
        )
        await service.update_snapshot(1)
        # single report: avg_confidence = (0.95 * 0.50) / 0.95 = 0.50
        assert snap.confidence_score == Decimal("0.50")

    async def test_confidence_is_1_00_when_no_reports(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        _, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            reports=[],
        )
        await service.update_snapshot(1)
        assert snap.confidence_score == Decimal("1.00")

    @freeze_time(_NOW)
    async def test_avg_status_value_persisted_on_snapshot(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        reports = [
            QueueReportFactory.build(
                status=ReportStatusEnum.SMALL, created_at=_NOW - timedelta(seconds=30)
            )
        ]
        _, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            reports=reports,
        )
        await service.update_snapshot(1)
        assert snap.avg_status_value == Decimal("1.00")

    async def test_avg_status_value_is_none_when_no_reports(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        _, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            reports=[],
        )
        await service.update_snapshot(1)
        assert snap.avg_status_value is None

    async def test_commits_db_session_after_update(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
        )
        await service.update_snapshot(1)
        mock_snapshot_repo.db_session.commit.assert_called_once()

    async def test_returns_updated_snapshot_instance(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        _, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
        )
        result = await service.update_snapshot(1)
        assert result is snap

    async def test_raises_snapshot_not_found_when_snapshot_is_missing(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_report_repo.list_recent_by_period_within_minutes.return_value = []
        mock_snapshot_repo.get_by_ru_id_and_meal_period.return_value = None

        with pytest.raises(QueueSnapshotNotFoundError):
            await service.update_snapshot(1)

    async def test_does_not_commit_when_snapshot_not_found(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_report_repo.list_recent_by_period_within_minutes.return_value = []
        mock_snapshot_repo.get_by_ru_id_and_meal_period.return_value = None

        with pytest.raises(QueueSnapshotNotFoundError):
            await service.update_snapshot(1)

        mock_snapshot_repo.db_session.commit.assert_not_called()

    async def test_raises_restaurant_not_found_when_restaurant_is_missing(
        self, service, mock_restaurant_repo
    ):
        mock_restaurant_repo.get_by_id.return_value = None
        with pytest.raises(RestaurantNotFoundError):
            await service.update_snapshot(99)

    async def test_queries_snapshot_with_correct_ru_id_and_meal_period(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            ru_id=5,
            meal_period=MealPeriodEnum.DINNER,
        )
        await service.update_snapshot(5)
        mock_snapshot_repo.get_by_ru_id_and_meal_period.assert_called_once_with(
            ru_id=5, meal_period=MealPeriodEnum.DINNER
        )

    async def test_calls_restaurant_repo_with_correct_ru_id(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
    ):
        self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
            ru_id=5,
        )
        await service.update_snapshot(5)
        mock_restaurant_repo.get_by_id.assert_called_once_with(5)

    async def test_publish_snapshot_called_after_successful_update(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
        mock_publish_snapshot,
    ):
        self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
        )
        await service.update_snapshot(1)

        mock_publish_snapshot.assert_called_once()

    async def test_publish_snapshot_called_with_correct_snapshot_and_public_id(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
        mock_publish_snapshot,
    ):
        restaurant, snap = self._setup_happy_path(
            mock_restaurant_repo,
            mock_meal_period_service,
            mock_report_repo,
            mock_snapshot_repo,
        )
        await service.update_snapshot(1)

        mock_publish_snapshot.assert_called_once_with(
            snapshot=snap,
            restaurant_public_id=restaurant.public_id,
        )

    async def test_publish_snapshot_not_called_when_snapshot_not_found(
        self,
        service,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_report_repo,
        mock_snapshot_repo,
        mock_publish_snapshot,
    ):
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_report_repo.list_recent_by_period_within_minutes.return_value = []
        mock_snapshot_repo.get_by_ru_id_and_meal_period.return_value = None

        with pytest.raises(QueueSnapshotNotFoundError):
            await service.update_snapshot(1)

        mock_publish_snapshot.assert_not_called()

    async def test_propagates_restaurant_closed_all_day_error(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.side_effect = RestaurantClosedAllDayError()
        with pytest.raises(RestaurantClosedAllDayError):
            await service.update_snapshot(1)

    async def test_propagates_outside_meal_hours_error(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()
        with pytest.raises(OutsideMealHoursError):
            await service.update_snapshot(1)

    async def test_propagates_meal_period_closed_error(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        mock_restaurant_repo.get_by_id.return_value = RestaurantFactory.build(id=1)
        mock_meal_period_service.resolve.side_effect = MealPeriodClosedError()
        with pytest.raises(MealPeriodClosedError):
            await service.update_snapshot(1)
