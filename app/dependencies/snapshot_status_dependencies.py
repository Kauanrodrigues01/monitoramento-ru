from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DBSessionDep
from app.dependencies.meal_period_dependencies import get_meal_period_service
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.snapshot_status_service import SnapshotStatusService


def get_snapshot_status_service(db_session: DBSessionDep) -> SnapshotStatusService:
    snapshot_repo = QueueSnapshotRepository(db_session=db_session)
    report_repo = QueueReportRepository(db_session=db_session)
    restaurant_repo = RestaurantRepository(db_session=db_session)
    meal_period_service = get_meal_period_service(db_session)
    return SnapshotStatusService(
        snapshot_repo=snapshot_repo,
        report_repo=report_repo,
        restaurant_repo=restaurant_repo,
        meal_period_service=meal_period_service,
    )


SnapshotStatusServiceDep = Annotated[
    SnapshotStatusService, Depends(get_snapshot_status_service)
]
