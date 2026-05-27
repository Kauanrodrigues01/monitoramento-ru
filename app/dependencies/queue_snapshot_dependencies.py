from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DBSessionDep
from app.dependencies.meal_period_dependencies import get_meal_period_service
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.queue_snapshot_service import QueueSnapshotService


def get_queue_snapshot_service(db_session: DBSessionDep) -> QueueSnapshotService:
    repo = QueueSnapshotRepository(db_session=db_session)
    restaurant_repo = RestaurantRepository(db_session=db_session)
    meal_period_service = get_meal_period_service(db_session)
    return QueueSnapshotService(
        repo=repo,
        restaurant_repo=restaurant_repo,
        meal_period_service=meal_period_service,
    )


QueueSnapshotServiceDep = Annotated[
    QueueSnapshotService, Depends(get_queue_snapshot_service)
]
