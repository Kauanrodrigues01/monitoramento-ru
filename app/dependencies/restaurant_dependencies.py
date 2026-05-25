from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DBSessionDep
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository
from app.services.restaurant_schedule_service import RestaurantScheduleService
from app.services.restaurant_service import RestaurantService


def get_restaurant_service(db_session: DBSessionDep) -> RestaurantService:
    return RestaurantService(repo=RestaurantRepository(db_session=db_session))


RestaurantServiceDep = Annotated[
    RestaurantService,
    Depends(get_restaurant_service),
]


def get_restaurant_schedule_service(
    db_session: DBSessionDep,
) -> RestaurantScheduleService:
    return RestaurantScheduleService(
        repo=RestaurantScheduleRepository(db_session=db_session),
        restaurant_repo=RestaurantRepository(db_session=db_session),
    )


RestaurantScheduleServiceDep = Annotated[
    RestaurantScheduleService,
    Depends(get_restaurant_schedule_service),
]
