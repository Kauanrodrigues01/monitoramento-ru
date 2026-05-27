from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.meal_period_dependencies import get_meal_period_service
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository
from app.services.debug_meal_period_service import DebugMealPeriodService
from app.services.meal_period_service import MealPeriodService


class TestGetMealPeriodServiceDebugMode:
    def test_should_return_debug_meal_period_service_when_debug_is_true(self):
        session = MagicMock(spec=AsyncSession)

        with patch(
            "app.dependencies.meal_period_dependencies.settings"
        ) as mock_settings:
            mock_settings.DEBUG = True
            service = get_meal_period_service(session)

        assert isinstance(service, DebugMealPeriodService)

    def test_should_not_use_session_when_debug_is_true(self):
        session = MagicMock(spec=AsyncSession)

        with patch(
            "app.dependencies.meal_period_dependencies.settings"
        ) as mock_settings:
            mock_settings.DEBUG = True
            service = get_meal_period_service(session)

        assert not hasattr(service, "schedule_repo")
        assert not hasattr(service, "schedule_exception_repo")


class TestGetMealPeriodServiceProductionMode:
    def test_should_return_meal_period_service_when_debug_is_false(self):
        session = MagicMock(spec=AsyncSession)

        with patch(
            "app.dependencies.meal_period_dependencies.settings"
        ) as mock_settings:
            mock_settings.DEBUG = False
            service = get_meal_period_service(session)

        assert isinstance(service, MealPeriodService)
        assert not isinstance(service, DebugMealPeriodService)

    def test_should_inject_schedule_repository(self):
        session = MagicMock(spec=AsyncSession)

        with patch(
            "app.dependencies.meal_period_dependencies.settings"
        ) as mock_settings:
            mock_settings.DEBUG = False
            service = get_meal_period_service(session)

        assert isinstance(service.schedule_repo, RestaurantScheduleRepository)

    def test_should_inject_schedule_exception_repository(self):
        session = MagicMock(spec=AsyncSession)

        with patch(
            "app.dependencies.meal_period_dependencies.settings"
        ) as mock_settings:
            mock_settings.DEBUG = False
            service = get_meal_period_service(session)

        assert isinstance(
            service.schedule_exception_repo, RestaurantScheduleExceptionRepository
        )

    def test_should_use_same_session_for_both_repositories(self):
        session = MagicMock(spec=AsyncSession)

        with patch(
            "app.dependencies.meal_period_dependencies.settings"
        ) as mock_settings:
            mock_settings.DEBUG = False
            service = get_meal_period_service(session)

        assert service.schedule_repo.db_session is session
        assert service.schedule_exception_repo.db_session is session
