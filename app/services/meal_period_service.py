from datetime import datetime

from app.core.logging import get_logger
from app.core.utils import infer_meal_period
from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.models.restaurant import ExceptionTypeEnum, MealPeriodEnum
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository


logger = get_logger(__name__)


class MealPeriodService:
    def __init__(
        self,
        schedule_repo: RestaurantScheduleRepository,
        schedule_exception_repo: RestaurantScheduleExceptionRepository,
    ):
        self.schedule_repo = schedule_repo
        self.schedule_exception_repo = schedule_exception_repo

    async def resolve(self, ru_id: int, at: datetime) -> MealPeriodEnum:
        """
        Resolve o período de refeição ativo para um restaurante em um dado momento.

        Ordem de prioridade:
        1. Exceção CLOSED sem meal_period → RestaurantClosedAllDayError
        2. Exceções CUSTOM_HOURS → sobrescrevem o horário regular
        3. Schedules regulares (fallback)
        4. Nenhum período encontrado → OutsideMealHoursError
        5. Exceção CLOSED com meal_period → MealPeriodClosedError
        """
        schedule_exceptions = await self.schedule_exception_repo.list_by_ru_id_and_date(
            ru_id=ru_id,
            exception_date=at.date(),
        )

        whole_day_closed = any(
            e.exception_type == ExceptionTypeEnum.CLOSED and e.meal_period is None
            for e in schedule_exceptions
        )
        if whole_day_closed:
            logger.debug("ru_id=%s fechado o dia todo em %s", ru_id, at.date())
            raise RestaurantClosedAllDayError()

        custom_hours = [
            e for e in schedule_exceptions
            if e.exception_type == ExceptionTypeEnum.CUSTOM_HOURS
        ]
        meal_period = infer_meal_period(at=at, schedules_exceptions=custom_hours)

        if meal_period is None:
            schedules = await self.schedule_repo.list_by_ru_id_and_weekday(
                ru_id=ru_id,
                weekday=at.weekday(),
                only_active=True,
            )
            meal_period = infer_meal_period(at=at, schedules=schedules)

        if meal_period is None:
            logger.debug("ru_id=%s fora do horário de funcionamento às %s", ru_id, at.time())
            raise OutsideMealHoursError()

        period_closed = any(
            e.exception_type == ExceptionTypeEnum.CLOSED and e.meal_period == meal_period
            for e in schedule_exceptions
        )
        if period_closed:
            logger.debug(
                "ru_id=%s período %s fechado por exceção em %s",
                ru_id,
                meal_period.value,
                at.date(),
            )
            raise MealPeriodClosedError()

        logger.debug("ru_id=%s período resolvido: %s", ru_id, meal_period.value)
        return meal_period
