from datetime import datetime
from uuid import uuid4

import pytest

from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.restaurant import MealPeriodEnum
from app.tests.unit.services.queue_report_service._base import (
    _make_queue_report,
)


class TestListRecentQueueReports:
    async def test_returns_list_of_reports_for_current_period(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
    ):
        expected = [
            _make_queue_report(ru_id=restaurant.id),
            _make_queue_report(ru_id=restaurant.id),
        ]
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.list_recent_by_period.return_value = expected

        result = await service.list_recent_queue_reports(restaurant.public_id)

        assert result is expected

    async def test_restaurant_not_found_raises_error(
        self, service, mock_restaurant_repo
    ):
        mock_restaurant_repo.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.list_recent_queue_reports(uuid4())

    async def test_returns_empty_list_when_no_reports(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.list_recent_by_period.return_value = []

        result = await service.list_recent_queue_reports(restaurant.public_id)

        assert result == []

    async def test_uses_datetime_now_to_resolve_meal_period(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
    ):
        from freezegun import freeze_time

        fixed_now = datetime(2025, 5, 25, 12, 0, 0)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.list_recent_by_period.return_value = []

        with freeze_time(fixed_now):
            await service.list_recent_queue_reports(restaurant.public_id)

        mock_meal_period_service.resolve.assert_called_once_with(
            ru_id=restaurant.id,
            at=fixed_now,
        )

    async def test_restaurant_closed_propagates_restaurant_closed_all_day_error(
        self, service, mock_restaurant_repo, mock_meal_period_service, restaurant
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.side_effect = RestaurantClosedAllDayError()

        with pytest.raises(RestaurantClosedAllDayError):
            await service.list_recent_queue_reports(restaurant.public_id)

    async def test_outside_hours_propagates_outside_meal_hours_error(
        self, service, mock_restaurant_repo, mock_meal_period_service, restaurant
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()

        with pytest.raises(OutsideMealHoursError):
            await service.list_recent_queue_reports(restaurant.public_id)

    async def test_period_closed_propagates_meal_period_closed_error(
        self, service, mock_restaurant_repo, mock_meal_period_service, restaurant
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.side_effect = MealPeriodClosedError()

        with pytest.raises(MealPeriodClosedError):
            await service.list_recent_queue_reports(restaurant.public_id)

    async def test_repo_called_with_limit_20_and_offset_0(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.list_recent_by_period.return_value = []

        await service.list_recent_queue_reports(restaurant.public_id)

        call_kwargs = mock_repo.list_recent_by_period.call_args.kwargs
        assert call_kwargs["limit"] == 20
        assert call_kwargs["offset"] == 0

    async def test_repo_called_with_correct_ru_id_meal_period_and_date(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
    ):
        from freezegun import freeze_time

        fixed_now = datetime(2025, 5, 25, 12, 0, 0)
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_meal_period_service.resolve.return_value = MealPeriodEnum.LUNCH
        mock_repo.list_recent_by_period.return_value = []

        with freeze_time(fixed_now):
            await service.list_recent_queue_reports(restaurant.public_id)

        call_kwargs = mock_repo.list_recent_by_period.call_args.kwargs
        assert call_kwargs["ru_id"] == restaurant.id
        assert call_kwargs["meal_period"] == MealPeriodEnum.LUNCH
        assert call_kwargs["day"] == fixed_now.date()
