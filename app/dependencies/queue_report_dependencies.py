from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DBSessionDep
from app.dependencies.meal_period_dependencies import get_meal_period_service
from app.dependencies.snapshot_status_dependencies import get_snapshot_status_service
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.queue_report_service import QueueReportService


def get_queue_report_service(db_session: DBSessionDep) -> QueueReportService:
    repo = QueueReportRepository(db_session=db_session)
    restaurant_repo = RestaurantRepository(db_session=db_session)
    snapshot_repo = QueueSnapshotRepository(db_session=db_session)
    meal_period_service = get_meal_period_service(db_session)
    snapshot_status_service = get_snapshot_status_service(db_session)
    return QueueReportService(
        repo=repo,
        restaurant_repo=restaurant_repo,
        snapshot_repo=snapshot_repo,
        meal_period_service=meal_period_service,
        snapshot_status_service=snapshot_status_service,
    )


QueueReportServiceDep = Annotated[QueueReportService, Depends(get_queue_report_service)]
