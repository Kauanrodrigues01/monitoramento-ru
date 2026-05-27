from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DBSessionDep
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository
from app.services.restaurant_schedule_exception_service import (
    RestaurantScheduleExceptionService,
)
from app.services.restaurant_schedule_service import RestaurantScheduleService
from app.services.restaurant_service import RestaurantService


def get_restaurant_service(db_session: DBSessionDep) -> RestaurantService:
    repo = RestaurantRepository(db_session=db_session)
    snapshot_repo = QueueSnapshotRepository(db_session=db_session)
    return RestaurantService(repo=repo, snapshot_repo=snapshot_repo)


RestaurantServiceDep = Annotated[
    RestaurantService,
    Depends(get_restaurant_service),
]


def get_restaurant_schedule_service(
    db_session: DBSessionDep,
) -> RestaurantScheduleService:
    repo = RestaurantScheduleRepository(db_session=db_session)
    restaurant_repo = RestaurantRepository(db_session=db_session)
    return RestaurantScheduleService(repo=repo, restaurant_repo=restaurant_repo)


RestaurantScheduleServiceDep = Annotated[
    RestaurantScheduleService,
    Depends(get_restaurant_schedule_service),
]


def get_restaurant_schedule_exception_service(
    db_session: DBSessionDep,
) -> RestaurantScheduleExceptionService:
    repo = RestaurantScheduleExceptionRepository(db_session=db_session)
    restaurant_repo = RestaurantRepository(db_session=db_session)
    return RestaurantScheduleExceptionService(repo=repo, restaurant_repo=restaurant_repo)


RestaurantScheduleExceptionServiceDep = Annotated[
    RestaurantScheduleExceptionService,
    Depends(get_restaurant_schedule_exception_service),
]
