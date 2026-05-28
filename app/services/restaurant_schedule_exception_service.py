from datetime import date, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger
from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.exceptions.restaurant_exceptions import (
    RestaurantNotFoundError,
    RestaurantScheduleExceptionAlreadyExistsError,
    RestaurantScheduleExceptionInvalidStateError,
    RestaurantScheduleExceptionNotFoundError,
)
from app.models.restaurant import (
    ExceptionTypeEnum,
    Restaurant,
    RestaurantScheduleException,
)
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.schemas.restaurant_schedule_exception_schemas import (
    RestaurantScheduleExceptionCreate,
    RestaurantScheduleExceptionUpdate,
)
from app.services.meal_period_service import MealPeriodService

logger = get_logger(__name__)


class RestaurantScheduleExceptionService:
    def __init__(
        self,
        repo: RestaurantScheduleExceptionRepository,
        restaurant_repo: RestaurantRepository,
        meal_period_service: MealPeriodService,
    ):
        self.repo = repo
        self.restaurant_repo = restaurant_repo
        self.meal_period_service = meal_period_service

    async def _get_restaurant_by_public_id_or_error(
        self, public_id: UUID
    ) -> Restaurant:
        restaurant = await self.restaurant_repo.get_by_public_id(public_id)
        if not restaurant:
            raise RestaurantNotFoundError()
        return restaurant

    async def create_restaurant_schedule_exception(
        self,
        restaurant_public_id: UUID,
        data: RestaurantScheduleExceptionCreate,
    ) -> RestaurantScheduleException:
        restaurant = await self._get_restaurant_by_public_id_or_error(
            restaurant_public_id
        )

        existing = await self.repo.get_by_ru_id_date_and_meal_period(
            ru_id=restaurant.id,
            exception_date=data.exception_date,
            meal_period=data.meal_period,
        )
        if existing:
            logger.warning(
                "Tentativa de criar exceção duplicada: ru_id=%s, date=%s, meal_period=%s",
                restaurant.id,
                data.exception_date,
                data.meal_period,
            )
            raise RestaurantScheduleExceptionAlreadyExistsError()

        try:
            exception = RestaurantScheduleException(
                ru_id=restaurant.id, **data.model_dump()
            )
            await self.repo.create(exception)
            await self.repo.db_session.commit()
            return exception
        except IntegrityError:
            await self.repo.db_session.rollback()
            raise RestaurantScheduleExceptionAlreadyExistsError()
        except Exception:
            await self.repo.db_session.rollback()
            raise

    async def get_active_exception(
        self,
        restaurant_public_id: UUID,
        at: datetime,
    ) -> RestaurantScheduleException | None:
        """Retorna a exceção de horário vigente para o período atual, ou None se não houver.

        Prioridade:
        1. CLOSED sem meal_period → dia inteiro fechado, retorna imediatamente.
        2. MealPeriodService resolve o período corrente:
           - OutsideMealHoursError / RestaurantClosedAllDayError → None
           - MealPeriodClosedError → retorna a exceção CLOSED do período
        3. Exceção (CLOSED ou CUSTOM_HOURS) que bate com o meal_period resolvido.
        """
        restaurant = await self._get_restaurant_by_public_id_or_error(restaurant_public_id)
        exceptions = await self.repo.list_by_ru_id_and_date(restaurant.id, at.date())

        if not exceptions:
            return None

        whole_day = next(
            (
                e for e in exceptions
                if e.meal_period is None and e.exception_type == ExceptionTypeEnum.CLOSED
            ),
            None,
        )
        if whole_day:
            return whole_day

        try:
            meal_period = await self.meal_period_service.resolve(restaurant.id, at)
        except (OutsideMealHoursError, RestaurantClosedAllDayError):
            return None
        except MealPeriodClosedError:
            # O MealPeriodService resolveu o período mas encontrou uma exceção CLOSED.
            # Retorna a primeira exceção CLOSED com meal_period definido — na prática
            # só há uma por período por data (garantido pelo constraint único).
            return next(
                (
                    e for e in exceptions
                    if e.exception_type == ExceptionTypeEnum.CLOSED
                    and e.meal_period is not None
                ),
                None,
            )

        return next((e for e in exceptions if e.meal_period == meal_period), None)

    async def list_restaurant_schedule_exceptions(
        self,
        restaurant_public_id: UUID,
        exception_date: date | None,
    ) -> list[RestaurantScheduleException]:
        restaurant = await self._get_restaurant_by_public_id_or_error(
            restaurant_public_id
        )

        if exception_date:
            return await self.repo.list_by_ru_id_and_date(restaurant.id, exception_date)

        return await self.repo.list_by_ru_id(restaurant.id)

    async def update_restaurant_schedule_exception(
        self,
        restaurant_public_id: UUID,
        schedule_exception_public_id: UUID,
        data: RestaurantScheduleExceptionUpdate,
    ) -> RestaurantScheduleException:
        restaurant = await self._get_restaurant_by_public_id_or_error(
            restaurant_public_id
        )

        exception = await self.repo.get_by_public_id(schedule_exception_public_id)
        if not exception:
            raise RestaurantScheduleExceptionNotFoundError()

        if exception.ru_id != restaurant.id:
            raise RestaurantScheduleExceptionNotFoundError()

        updated_data = data.model_dump(exclude_unset=True)
        for field, value in updated_data.items():
            setattr(exception, field, value)

        # valida estado resultante após aplicar o patch parcial
        if exception.exception_type == ExceptionTypeEnum.CUSTOM_HOURS:
            if exception.opens_at is None or exception.closes_at is None:
                raise RestaurantScheduleExceptionInvalidStateError()
            if exception.opens_at >= exception.closes_at:
                raise RestaurantScheduleExceptionInvalidStateError()
        elif exception.exception_type == ExceptionTypeEnum.CLOSED:
            if exception.opens_at is not None or exception.closes_at is not None:
                raise RestaurantScheduleExceptionInvalidStateError()

        try:
            await self.repo.db_session.commit()
            await self.repo.db_session.refresh(exception)
            return exception
        except IntegrityError:
            await self.repo.db_session.rollback()
            raise RestaurantScheduleExceptionAlreadyExistsError()
        except Exception:
            await self.repo.db_session.rollback()
            raise
