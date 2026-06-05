from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.metrics_dependencies import get_metrics_service
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.meal_period_service import MealPeriodService
from app.services.metrics_service import MetricsService


class TestGetMetricsService:
    def test_should_return_metrics_service_instance(self):
        session = MagicMock(spec=AsyncSession)

        service = get_metrics_service(session)

        assert isinstance(service, MetricsService)

    def test_should_inject_queue_snapshot_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_metrics_service(session)

        assert isinstance(service.snapshot_repo, QueueSnapshotRepository)

    def test_should_inject_queue_report_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_metrics_service(session)

        assert isinstance(service.report_repo, QueueReportRepository)

    def test_should_inject_restaurant_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_metrics_service(session)

        assert isinstance(service.restaurant_repo, RestaurantRepository)

    def test_should_inject_meal_period_service(self):
        session = MagicMock(spec=AsyncSession)

        service = get_metrics_service(session)

        assert isinstance(service.meal_period_service, MealPeriodService)

    def test_should_use_same_session_for_repositories(self):
        session = MagicMock(spec=AsyncSession)

        service = get_metrics_service(session)

        assert service.snapshot_repo.db_session is session
        assert service.report_repo.db_session is session
        assert service.restaurant_repo.db_session is session
