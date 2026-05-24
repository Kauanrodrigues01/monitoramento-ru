from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DBSessionDep
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.restaurant_service import RestaurantService


def get_restaurant_service(db_session: DBSessionDep) -> RestaurantService:
    return RestaurantService(repo=RestaurantRepository(db_session=db_session))


RestaurantServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]
