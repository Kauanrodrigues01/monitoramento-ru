from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.exceptions.queue_snapshot_exceptions import (
    QueueSnapshotBulkLimitExceededError,
    QueueSnapshotNotFoundError,
)
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.queue_snapshot import QueueSnapshot, SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.meal_period_service import MealPeriodService
from app.services.queue_snapshot_service import BULK_LIMIT, QueueSnapshotService
from app.tests.factories.restaurant_model_factory import RestaurantFactory


def _make_snapshot(
    ru_id: int = 1,
    meal_period: MealPeriodEnum = MealPeriodEnum.LUNCH,
    current_status: SnapshotStatusEnum = SnapshotStatusEnum.NO_DATA,
    reports_last_15m: int = 0,
    last_report_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> QueueSnapshot:
    snapshot = QueueSnapshot()
    snapshot.ru_id = ru_id
    snapshot.meal_period = meal_period
    snapshot.current_status = current_status
    snapshot.reports_last_15m = reports_last_15m
    snapshot.last_report_at = last_report_at
    snapshot.updated_at = updated_at or datetime(2026, 5, 26, 12, 0, 0)
    return snapshot


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=QueueSnapshotRepository)


@pytest.fixture
def mock_restaurant_repo():
    return AsyncMock(spec=RestaurantRepository)


@pytest.fixture
def mock_meal_period_service():
    return AsyncMock(spec=MealPeriodService)


@pytest.fixture
def service(mock_repo, mock_restaurant_repo, mock_meal_period_service):
    return QueueSnapshotService(
        repo=mock_repo,
        restaurant_repo=mock_restaurant_repo,
        meal_period_service=mock_meal_period_service,
    )


# ===== GET STATUS =====
class TestGetStatus:
    @pytest.mark.asyncio
    async def test_should_return_snapshot_when_found(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=1)
        snapshot = _make_snapshot(ru_id=1, meal_period=MealPeriodEnum.LUNCH)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.get_by_ru_id_and_meal_period.return_value = snapshot

        result = await service.get_status(restaurant.public_id)

        assert result is snapshot

    @pytest.mark.asyncio
    async def test_should_raise_restaurant_not_found(
        self, service, mock_restaurant_repo
    ):
        mock_restaurant_repo.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.get_status(uuid4())

    @pytest.mark.asyncio
    async def test_should_raise_snapshot_not_found_when_snapshot_is_none(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=1)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.get_by_ru_id_and_meal_period.return_value = None

        with pytest.raises(QueueSnapshotNotFoundError):
            await service.get_status(restaurant.public_id)

    @pytest.mark.asyncio
    async def test_should_propagate_outside_meal_hours_error(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=1)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()

        with pytest.raises(OutsideMealHoursError):
            await service.get_status(restaurant.public_id)

    @pytest.mark.asyncio
    async def test_should_propagate_restaurant_closed_all_day_error(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=1)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.side_effect = RestaurantClosedAllDayError()

        with pytest.raises(RestaurantClosedAllDayError):
            await service.get_status(restaurant.public_id)

    @pytest.mark.asyncio
    async def test_should_propagate_meal_period_closed_error(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=1)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.side_effect = MealPeriodClosedError()

        with pytest.raises(MealPeriodClosedError):
            await service.get_status(restaurant.public_id)

    @pytest.mark.asyncio
    async def test_should_query_snapshot_with_correct_ru_id_and_meal_period(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=7)
        snapshot = _make_snapshot(ru_id=7, meal_period=MealPeriodEnum.DINNER)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.DINNER
        mock_repo.get_by_ru_id_and_meal_period.return_value = snapshot

        await service.get_status(restaurant.public_id)

        mock_repo.get_by_ru_id_and_meal_period.assert_called_once_with(
            ru_id=7, meal_period=MealPeriodEnum.DINNER
        )

    @pytest.mark.asyncio
    async def test_should_call_meal_period_service_with_correct_ru_id(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=5)
        snapshot = _make_snapshot(ru_id=5)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.get_by_ru_id_and_meal_period.return_value = snapshot

        await service.get_status(restaurant.public_id)

        call_kwargs = mock_meal_period_service.resolve.call_args
        assert call_kwargs.kwargs["ru_id"] == 5

    @pytest.mark.asyncio
    async def test_should_not_query_snapshot_when_restaurant_not_found(
        self, service, mock_repo, mock_restaurant_repo
    ):
        mock_restaurant_repo.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.get_status(uuid4())

        mock_repo.get_by_ru_id_and_meal_period.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_not_call_meal_period_service_when_restaurant_not_found(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        mock_restaurant_repo.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.get_status(uuid4())

        mock_meal_period_service.resolve.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_call_get_by_public_id_with_correct_id(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=1)
        public_id = restaurant.public_id
        snapshot = _make_snapshot(ru_id=1)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.get_by_ru_id_and_meal_period.return_value = snapshot

        await service.get_status(public_id)

        mock_restaurant_repo.get_by_public_id.assert_called_once_with(public_id)


# ===== GET BULK STATUS =====
class TestGetBulkStatus:
    @pytest.mark.asyncio
    async def test_should_raise_bulk_limit_exceeded_when_ids_exceed_limit(
        self, service
    ):
        public_ids = [uuid4() for _ in range(BULK_LIMIT + 1)]

        with pytest.raises(QueueSnapshotBulkLimitExceededError):
            await service.get_bulk_status(public_ids)

    @pytest.mark.asyncio
    async def test_should_not_raise_at_exact_bulk_limit(
        self, service, mock_restaurant_repo, mock_meal_period_service, mock_repo
    ):
        public_ids = [uuid4() for _ in range(BULK_LIMIT)]
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = []

        result = await service.get_bulk_status(public_ids)

        assert result == []

    @pytest.mark.asyncio
    async def test_should_not_call_any_repo_when_limit_exceeded(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        public_ids = [uuid4() for _ in range(BULK_LIMIT + 1)]

        with pytest.raises(QueueSnapshotBulkLimitExceededError):
            await service.get_bulk_status(public_ids)

        mock_restaurant_repo.get_bulk_by_public_ids.assert_not_called()
        mock_meal_period_service.resolve.assert_not_called()
        mock_repo.get_bulk_by_ru_ids_and_meal_period.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_empty_list_for_empty_ids(
        self, service, mock_restaurant_repo
    ):
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = []

        result = await service.get_bulk_status([])

        assert result == []

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_restaurants_found(
        self, service, mock_restaurant_repo
    ):
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = []

        result = await service.get_bulk_status([uuid4(), uuid4()])

        assert result == []

    @pytest.mark.asyncio
    async def test_should_not_query_snapshots_when_no_restaurants_found(
        self, service, mock_repo, mock_restaurant_repo
    ):
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = []

        await service.get_bulk_status([uuid4()])

        mock_repo.get_bulk_by_ru_ids_and_meal_period.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_all_restaurants_closed_all_day(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurants = [RestaurantFactory.build(id=i) for i in range(1, 4)]
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = restaurants
        mock_meal_period_service.resolve.side_effect = RestaurantClosedAllDayError()

        result = await service.get_bulk_status([r.public_id for r in restaurants])

        assert result == []
        mock_repo.get_bulk_by_ru_ids_and_meal_period.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_all_restaurants_outside_hours(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurants = [RestaurantFactory.build(id=i) for i in range(1, 3)]
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = restaurants
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()

        result = await service.get_bulk_status([r.public_id for r in restaurants])

        assert result == []

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_all_meal_periods_closed(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurants = [RestaurantFactory.build(id=i) for i in range(1, 3)]
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = restaurants
        mock_meal_period_service.resolve.side_effect = MealPeriodClosedError()

        result = await service.get_bulk_status([r.public_id for r in restaurants])

        assert result == []

    @pytest.mark.asyncio
    async def test_should_skip_closed_restaurant_and_include_open_one(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        closed = RestaurantFactory.build(id=1)
        open_ = RestaurantFactory.build(id=2)
        snapshot = _make_snapshot(ru_id=2, meal_period=MealPeriodEnum.LUNCH)
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = [closed, open_]
        mock_meal_period_service.resolve.side_effect = [
            RestaurantClosedAllDayError(),
            MealPeriodEnum.LUNCH,
        ]
        mock_repo.get_bulk_by_ru_ids_and_meal_period.return_value = [snapshot]

        result = await service.get_bulk_status([closed.public_id, open_.public_id])

        assert len(result) == 1
        assert result[0].restaurant_public_id == open_.public_id

    @pytest.mark.asyncio
    async def test_should_return_correct_bulk_item_fields(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=3)
        last_report = datetime(2026, 5, 26, 11, 30, 0)
        updated = datetime(2026, 5, 26, 11, 45, 0)
        snapshot = _make_snapshot(
            ru_id=3,
            meal_period=MealPeriodEnum.LUNCH,
            current_status=SnapshotStatusEnum.MEDIUM,
            reports_last_15m=5,
            last_report_at=last_report,
            updated_at=updated,
        )
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = [restaurant]
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.get_bulk_by_ru_ids_and_meal_period.return_value = [snapshot]

        result = await service.get_bulk_status([restaurant.public_id])

        assert len(result) == 1
        item = result[0]
        assert item.restaurant_public_id == restaurant.public_id
        assert item.meal_period == MealPeriodEnum.LUNCH
        assert item.current_status == SnapshotStatusEnum.MEDIUM
        assert item.reports_last_15m == 5
        assert item.last_report_at == last_report
        assert item.updated_at == updated

    @pytest.mark.asyncio
    async def test_should_accept_last_report_at_as_none_in_bulk_item(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=4)
        snapshot = _make_snapshot(ru_id=4, last_report_at=None)
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = [restaurant]
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.get_bulk_by_ru_ids_and_meal_period.return_value = [snapshot]

        result = await service.get_bulk_status([restaurant.public_id])

        assert result[0].last_report_at is None

    @pytest.mark.asyncio
    async def test_should_group_restaurants_by_meal_period(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        lunch_ru = RestaurantFactory.build(id=1)
        dinner_ru = RestaurantFactory.build(id=2)
        lunch_snapshot = _make_snapshot(ru_id=1, meal_period=MealPeriodEnum.LUNCH)
        dinner_snapshot = _make_snapshot(ru_id=2, meal_period=MealPeriodEnum.DINNER)

        mock_restaurant_repo.get_bulk_by_public_ids.return_value = [lunch_ru, dinner_ru]
        mock_meal_period_service.resolve.side_effect = [
            MealPeriodEnum.LUNCH,
            MealPeriodEnum.DINNER,
        ]
        mock_repo.get_bulk_by_ru_ids_and_meal_period.side_effect = [
            [lunch_snapshot],
            [dinner_snapshot],
        ]

        result = await service.get_bulk_status(
            [lunch_ru.public_id, dinner_ru.public_id]
        )

        assert len(result) == 2
        assert mock_repo.get_bulk_by_ru_ids_and_meal_period.call_count == 2

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_snapshots_not_found_for_restaurants(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurant = RestaurantFactory.build(id=1)
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = [restaurant]
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.get_bulk_by_ru_ids_and_meal_period.return_value = []

        result = await service.get_bulk_status([restaurant.public_id])

        assert result == []

    @pytest.mark.asyncio
    async def test_should_not_call_meal_period_service_when_no_restaurants_found(
        self, service, mock_restaurant_repo, mock_meal_period_service
    ):
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = []

        await service.get_bulk_status([uuid4()])

        mock_meal_period_service.resolve.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_call_get_bulk_by_public_ids_with_correct_ids(
        self, service, mock_restaurant_repo
    ):
        public_ids = [uuid4(), uuid4()]
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = []

        await service.get_bulk_status(public_ids)

        mock_restaurant_repo.get_bulk_by_public_ids.assert_called_once_with(public_ids)

    @pytest.mark.asyncio
    async def test_should_call_resolve_for_each_restaurant(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        restaurants = [RestaurantFactory.build(id=i) for i in range(1, 4)]
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = restaurants
        mock_meal_period_service.resolve.side_effect = [MealPeriodEnum.LUNCH] * 3
        mock_repo.get_bulk_by_ru_ids_and_meal_period.return_value = []

        await service.get_bulk_status([r.public_id for r in restaurants])

        assert mock_meal_period_service.resolve.call_count == 3

    @pytest.mark.asyncio
    async def test_should_pass_correct_ru_ids_to_snapshot_repo(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        r1 = RestaurantFactory.build(id=10)
        r2 = RestaurantFactory.build(id=20)
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = [r1, r2]
        mock_meal_period_service.resolve.side_effect = [
            MealPeriodEnum.LUNCH,
            MealPeriodEnum.LUNCH,
        ]
        mock_repo.get_bulk_by_ru_ids_and_meal_period.return_value = []

        await service.get_bulk_status([r1.public_id, r2.public_id])

        call_args = mock_repo.get_bulk_by_ru_ids_and_meal_period.call_args
        ru_ids_passed = call_args.args[0]
        assert set(ru_ids_passed) == {10, 20}

    @pytest.mark.asyncio
    async def test_should_query_each_meal_period_group_once(
        self, service, mock_repo, mock_restaurant_repo, mock_meal_period_service
    ):
        r1 = RestaurantFactory.build(id=1)
        r2 = RestaurantFactory.build(id=2)
        r3 = RestaurantFactory.build(id=3)
        mock_restaurant_repo.get_bulk_by_public_ids.return_value = [r1, r2, r3]
        mock_meal_period_service.resolve.side_effect = [
            MealPeriodEnum.LUNCH,
            MealPeriodEnum.LUNCH,
            MealPeriodEnum.LUNCH,
        ]
        s1 = _make_snapshot(ru_id=1)
        s2 = _make_snapshot(ru_id=2)
        s3 = _make_snapshot(ru_id=3)
        mock_repo.get_bulk_by_ru_ids_and_meal_period.return_value = [s1, s2, s3]

        result = await service.get_bulk_status(
            [r1.public_id, r2.public_id, r3.public_id]
        )

        mock_repo.get_bulk_by_ru_ids_and_meal_period.assert_called_once()
        assert len(result) == 3
