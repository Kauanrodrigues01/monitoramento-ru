from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.queue_snapshot_dependencies import get_queue_snapshot_service
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.meal_period_service import MealPeriodService
from app.services.queue_snapshot_service import QueueSnapshotService


class TestGetQueueSnapshotService:
    def test_should_return_queue_snapshot_service_instance(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_snapshot_service(session)

        assert isinstance(service, QueueSnapshotService)

    def test_should_inject_queue_snapshot_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_snapshot_service(session)

        assert isinstance(service.repo, QueueSnapshotRepository)

    def test_should_inject_restaurant_repository(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_snapshot_service(session)

        assert isinstance(service.restaurant_repo, RestaurantRepository)

    def test_should_inject_meal_period_service(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_snapshot_service(session)

        assert isinstance(service.meal_period_service, MealPeriodService)

    def test_should_use_same_session_for_repositories(self):
        session = MagicMock(spec=AsyncSession)

        service = get_queue_snapshot_service(session)

        assert service.repo.db_session is session
        assert service.restaurant_repo.db_session is session
