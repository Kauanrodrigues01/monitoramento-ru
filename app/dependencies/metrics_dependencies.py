from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DBSessionDep
from app.dependencies.meal_period_dependencies import get_meal_period_service
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.metrics_service import MetricsService


def get_metrics_service(db_session: DBSessionDep) -> MetricsService:
    snapshot_repo = QueueSnapshotRepository(db_session=db_session)
    report_repo = QueueReportRepository(db_session=db_session)
    restaurant_repo = RestaurantRepository(db_session=db_session)
    meal_period_service = get_meal_period_service(db_session)
    return MetricsService(
        snapshot_repo=snapshot_repo,
        report_repo=report_repo,
        restaurant_repo=restaurant_repo,
        meal_period_service=meal_period_service,
    )


MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]
