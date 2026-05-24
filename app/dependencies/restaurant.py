from typing import Annotated

from fastapi import Depends

from dependencies.database import DBSessionDep
from repositories.restaurant_repository import RestaurantRepository
from services.restaurant_service import RestaurantService


def get_restaurant_service(db_session: DBSessionDep) -> RestaurantService:
    return RestaurantService(repo=RestaurantRepository(db_session=db_session))


RestaurantServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]
