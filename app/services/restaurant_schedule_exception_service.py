from datetime import date
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger
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

logger = get_logger(__name__)


class RestaurantScheduleExceptionService:
    def __init__(
        self,
        repo: RestaurantScheduleExceptionRepository,
        restaurant_repo: RestaurantRepository,
    ):
        self.repo = repo
        self.restaurant_repo = restaurant_repo

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
