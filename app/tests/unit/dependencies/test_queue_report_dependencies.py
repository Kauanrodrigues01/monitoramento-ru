from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.queue_report_dependencies import get_queue_report_service
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.meal_period_service import MealPeriodService
from app.services.queue_report_service import QueueReportService


class TestGetQueueReportService:
    def test_should_return_queue_report_service_instance(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_report_service(session)

        assert isinstance(service, QueueReportService)

    def test_should_inject_queue_report_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_report_service(session)

        assert isinstance(service.repo, QueueReportRepository)

    def test_should_inject_restaurant_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_report_service(session)

        assert isinstance(service.restaurant_repo, RestaurantRepository)

    def test_should_inject_meal_period_service(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_report_service(session)

        assert isinstance(service.meal_period_service, MealPeriodService)

    def test_should_use_same_session_for_repositories(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_report_service(session)

        assert service.repo.db_session is session
        assert service.restaurant_repo.db_session is session
