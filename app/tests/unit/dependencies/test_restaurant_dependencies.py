from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.restaurant_dependencies import (
    get_restaurant_schedule_service,
    get_restaurant_service,
)
from app.repositories.restaurant_repository import (
    RestaurantRepository,
    RestaurantScheduleRepository,
)
from app.services.restaurant_service import RestaurantScheduleService, RestaurantService


class TestGetRestaurantService:
    def test_should_return_restaurant_service_instance(self):
        session = MagicMock(spec=AsyncSession)

        service = get_restaurant_service(session)

        assert isinstance(service, RestaurantService)

    def test_should_inject_restaurant_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_restaurant_service(session)

        assert isinstance(service.repo, RestaurantRepository)

    def test_should_use_provided_session_in_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_restaurant_service(session)

        assert service.repo.db_session is session


class TestGetRestaurantScheduleService:
    def test_should_return_restaurant_schedule_service_instance(self):
        session = MagicMock(spec=AsyncSession)

        service = get_restaurant_schedule_service(session)

        assert isinstance(service, RestaurantScheduleService)

    def test_should_inject_schedule_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_restaurant_schedule_service(session)

        assert isinstance(service.repo, RestaurantScheduleRepository)

    def test_should_inject_restaurant_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_restaurant_schedule_service(session)

        assert isinstance(service.restaurant_repo, RestaurantRepository)

    def test_should_use_same_session_for_both_repositories(self):
        session = MagicMock(spec=AsyncSession)

        service = get_restaurant_schedule_service(session)

        assert service.repo.db_session is session
        assert service.restaurant_repo.db_session is session
