from typing import Annotated

from fastapi import Depends

from app.dependencies.database import DBSessionDep
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository
from app.services.meal_period_service import MealPeriodService
from app.services.queue_report_service import QueueReportService


def get_meal_period_service(db_session: DBSessionDep) -> MealPeriodService:
    return MealPeriodService(
        schedule_repo=RestaurantScheduleRepository(db_session=db_session),
        schedule_exception_repo=RestaurantScheduleExceptionRepository(db_session=db_session),
    )


MealPeriodServiceDep = Annotated[MealPeriodService, Depends(get_meal_period_service)]


def get_queue_report_service(db_session: DBSessionDep) -> QueueReportService:
    return QueueReportService(
        repo=QueueReportRepository(db_session=db_session),
        restaurant_repo=RestaurantRepository(db_session=db_session),
        meal_period_service=get_meal_period_service(db_session),
    )


QueueReportServiceDep = Annotated[QueueReportService, Depends(get_queue_report_service)]
