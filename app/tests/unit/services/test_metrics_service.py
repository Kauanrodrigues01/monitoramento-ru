from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.models.queue_snapshot import SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.metrics_schemas import MetricsSummaryResponse
from app.services.meal_period_service import MealPeriodService
from app.services.metrics_service import MetricsService
from app.tests.factories.models.unit.queue_snapshot_model_factory import (
    QueueSnapshotFactory,
)
from app.tests.factories.models.unit.restaurant_model_factory import RestaurantFactory


@pytest.fixture
def mock_snapshot_repo():
    return AsyncMock(spec=QueueSnapshotRepository)


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
    mock_snapshot_repo, mock_report_repo, mock_restaurant_repo, mock_meal_period_service
):
    return MetricsService(
        snapshot_repo=mock_snapshot_repo,
        report_repo=mock_report_repo,
        restaurant_repo=mock_restaurant_repo,
        meal_period_service=mock_meal_period_service,
    )


class TestGetSummary:
    @pytest.mark.asyncio
    async def test_should_return_metrics_summary_response_schema(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        mock_restaurant_repo.count_active.return_value = 3
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 5
        mock_report_repo.count_today.return_value = 20
        mock_snapshot_repo.list_all.return_value = []

        result = await service.get_summary()

        assert isinstance(result, MetricsSummaryResponse)

    @pytest.mark.asyncio
    async def test_should_return_total_active_restaurants(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        mock_restaurant_repo.count_active.return_value = 5
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []

        result = await service.get_summary()

        assert result.total_active_restaurants == 5
        mock_restaurant_repo.count_active.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_count_open_now_for_each_restaurant(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        restaurants = [RestaurantFactory.build(id=i) for i in range(1, 4)]
        mock_restaurant_repo.count_active.return_value = 3
        mock_restaurant_repo.get_all.return_value = restaurants
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH

        result = await service.get_summary()

        assert result.open_now == 3

    @pytest.mark.asyncio
    async def test_should_exclude_closed_restaurants_from_open_now(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        restaurants = [RestaurantFactory.build(id=i) for i in range(1, 4)]
        mock_restaurant_repo.count_active.return_value = 3
        mock_restaurant_repo.get_all.return_value = restaurants
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []
        mock_meal_period_service.resolve.side_effect = RestaurantClosedAllDayError()

        result = await service.get_summary()

        assert result.open_now == 0

    @pytest.mark.asyncio
    async def test_should_exclude_outside_meal_hours_from_open_now(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        restaurants = [RestaurantFactory.build(id=1), RestaurantFactory.build(id=2)]
        mock_restaurant_repo.count_active.return_value = 2
        mock_restaurant_repo.get_all.return_value = restaurants
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()

        result = await service.get_summary()

        assert result.open_now == 0

    @pytest.mark.asyncio
    async def test_should_exclude_meal_period_closed_from_open_now(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        restaurants = [RestaurantFactory.build(id=1)]
        mock_restaurant_repo.count_active.return_value = 1
        mock_restaurant_repo.get_all.return_value = restaurants
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []
        mock_meal_period_service.resolve.side_effect = MealPeriodClosedError()

        result = await service.get_summary()

        assert result.open_now == 0

    @pytest.mark.asyncio
    async def test_should_count_partial_open_restaurants(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        restaurants = [RestaurantFactory.build(id=i) for i in range(1, 4)]
        mock_restaurant_repo.count_active.return_value = 3
        mock_restaurant_repo.get_all.return_value = restaurants
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []
        mock_meal_period_service.resolve.side_effect = [
            MealPeriodEnum.LUNCH,
            RestaurantClosedAllDayError(),
            MealPeriodEnum.DINNER,
        ]

        result = await service.get_summary()

        assert result.open_now == 2

    @pytest.mark.asyncio
    async def test_should_call_count_within_minutes_with_15(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 7
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []

        result = await service.get_summary()

        assert result.reports_last_15m == 7
        mock_report_repo.count_within_minutes.assert_called_once_with(minutes=15)

    @pytest.mark.asyncio
    async def test_should_return_reports_today(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 33
        mock_snapshot_repo.list_all.return_value = []

        result = await service.get_summary()

        assert result.reports_today == 33
        mock_report_repo.count_today.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_build_status_distribution_from_snapshots(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        snapshots = [
            QueueSnapshotFactory.build(current_status=SnapshotStatusEnum.SMALL),
            QueueSnapshotFactory.build(current_status=SnapshotStatusEnum.SMALL),
            QueueSnapshotFactory.build(current_status=SnapshotStatusEnum.LARGE),
            QueueSnapshotFactory.build(current_status=SnapshotStatusEnum.NO_DATA),
        ]
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = snapshots

        result = await service.get_summary()

        assert result.status_distribution == {
            "SMALL": 2,
            "LARGE": 1,
            "NO_DATA": 1,
        }

    @pytest.mark.asyncio
    async def test_should_return_empty_status_distribution_when_no_snapshots(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []

        result = await service.get_summary()

        assert result.status_distribution == {}

    @pytest.mark.asyncio
    async def test_should_return_none_avg_confidence_when_no_snapshots(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []

        result = await service.get_summary()

        assert result.avg_confidence is None

    @pytest.mark.asyncio
    async def test_should_return_none_avg_confidence_when_all_snapshots_are_no_data(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        snapshots = [
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.NO_DATA,
                confidence_score=Decimal("0.50"),
            ),
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.NO_DATA,
                confidence_score=Decimal("1.00"),
            ),
        ]
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = snapshots

        result = await service.get_summary()

        assert result.avg_confidence is None

    @pytest.mark.asyncio
    async def test_should_exclude_no_data_snapshots_from_avg_confidence(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        snapshots = [
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.SMALL,
                confidence_score=Decimal("0.80"),
            ),
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.NO_DATA,
                confidence_score=Decimal("0.20"),
            ),
        ]
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = snapshots

        result = await service.get_summary()

        assert result.avg_confidence == 0.80

    @pytest.mark.asyncio
    async def test_should_calculate_avg_confidence_across_scored_snapshots(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        snapshots = [
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.SMALL,
                confidence_score=Decimal("0.60"),
            ),
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.LARGE,
                confidence_score=Decimal("0.40"),
            ),
        ]
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = snapshots

        result = await service.get_summary()

        assert result.avg_confidence == 0.50

    @pytest.mark.asyncio
    async def test_should_round_avg_confidence_to_two_decimal_places(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        snapshots = [
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.SMALL,
                confidence_score=Decimal("0.70"),
            ),
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.MEDIUM,
                confidence_score=Decimal("0.80"),
            ),
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.LARGE,
                confidence_score=Decimal("0.90"),
            ),
        ]
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = snapshots

        result = await service.get_summary()

        assert result.avg_confidence == 0.80

    @pytest.mark.asyncio
    async def test_should_include_all_non_no_data_statuses_in_avg_confidence(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        snapshots = [
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.NO_QUEUE,
                confidence_score=Decimal("1.00"),
            ),
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.FOOD_ENDED,
                confidence_score=Decimal("0.50"),
            ),
            QueueSnapshotFactory.build(
                current_status=SnapshotStatusEnum.NO_DATA,
                confidence_score=Decimal("0.10"),
            ),
        ]
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = snapshots

        result = await service.get_summary()

        assert result.avg_confidence == 0.75

    @pytest.mark.asyncio
    async def test_should_call_get_all_restaurants_with_only_active(
        self,
        service,
        mock_snapshot_repo,
        mock_report_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
    ):
        mock_restaurant_repo.count_active.return_value = 0
        mock_restaurant_repo.get_all.return_value = []
        mock_report_repo.count_within_minutes.return_value = 0
        mock_report_repo.count_today.return_value = 0
        mock_snapshot_repo.list_all.return_value = []

        await service.get_summary()

        mock_restaurant_repo.get_all.assert_called_once_with(only_active=True)
