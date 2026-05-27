from typing import Annotated

from fastapi import Depends

from app.core.settings import settings
from app.dependencies.database import DBSessionDep
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository
from app.services.debug_meal_period_service import DebugMealPeriodService
from app.services.meal_period_service import MealPeriodService


def get_meal_period_service(db_session: DBSessionDep) -> MealPeriodService:
    if settings.DEBUG:
        return DebugMealPeriodService()
    schedule_repo = RestaurantScheduleRepository(db_session=db_session)
    schedule_exception_repo = RestaurantScheduleExceptionRepository(db_session=db_session)
    return MealPeriodService(
        schedule_repo=schedule_repo,
        schedule_exception_repo=schedule_exception_repo,
    )


MealPeriodServiceDep = Annotated[MealPeriodService, Depends(get_meal_period_service)]
