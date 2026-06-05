from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger
from app.exceptions.restaurant_exceptions import (
    RestaurantScheduleAlreadyExistsError,
    RestaurantScheduleNotFoundError,
    RestaurantScheduleOpensBeforeClosesError,
)
from app.models.restaurant import MealPeriodEnum, RestaurantSchedule
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository
from app.schemas.restaurant_schedule_schemas import (
    RestaurantScheduleCreate,
    RestaurantScheduleUpdate,
)
from app.services._mixins import RestaurantResolverMixin

logger = get_logger(__name__)


class RestaurantScheduleService(RestaurantResolverMixin):
    def __init__(
        self,
        repo: RestaurantScheduleRepository,
        restaurant_repo: RestaurantRepository,
    ):
        self.repo = repo
        self.restaurant_repo = restaurant_repo

    async def create_restaurant_schedule(
        self, public_id: UUID, restaurant_schedule_data: RestaurantScheduleCreate
    ) -> RestaurantSchedule:
        data = restaurant_schedule_data
        restaurant = await self._get_restaurant_by_public_id_or_error(public_id)

        existing = await self.repo.get_by_ru_id_weekday_and_meal_period(
            ru_id=restaurant.id, weekday=data.weekday, meal_period=data.meal_period
        )

        if existing:
            logger.warning(
                "Tentativa de criar Restaurant Schedule duplicado: %s, %s, %s",
                restaurant.id,
                data.weekday,
                data.meal_period,
            )
            raise RestaurantScheduleAlreadyExistsError()

        try:
            restaurant_schedule = RestaurantSchedule(
                ru_id=restaurant.id, **data.model_dump()
            )
            await self.repo.create(restaurant_schedule)
            await self.repo.db_session.commit()
            return restaurant_schedule
        except IntegrityError:
            await self.repo.db_session.rollback()
            raise RestaurantScheduleAlreadyExistsError()
        except Exception:
            await self.repo.db_session.rollback()
            raise

    async def list_restaurant_schedules(
        self, public_id: UUID, meal_period: MealPeriodEnum | None
    ) -> list[RestaurantSchedule]:
        restaurant = await self._get_restaurant_by_public_id_or_error(public_id)

        if meal_period:
            return await self.repo.list_by_ru_id_and_meal_period(
                restaurant.id, meal_period
            )

        return await self.repo.list_by_ru_id(restaurant.id)

    async def update_restaurant_schedule(
        self,
        restaurant_public_id: UUID,
        schedule_public_id: UUID,
        restaurant_schedule_data: RestaurantScheduleUpdate,
    ) -> RestaurantSchedule:
        restaurant = await self._get_restaurant_by_public_id_or_error(
            restaurant_public_id
        )

        restaurant_schedule = await self.repo.get_by_public_id(schedule_public_id)

        if not restaurant_schedule:
            raise RestaurantScheduleNotFoundError()

        if restaurant.id != restaurant_schedule.ru_id:
            raise RestaurantScheduleNotFoundError()

        updated_data = restaurant_schedule_data.model_dump(
            exclude_none=True, exclude_unset=True
        )

        for field, value in updated_data.items():
            setattr(restaurant_schedule, field, value)

        if restaurant_schedule.opens_at >= restaurant_schedule.closes_at:
            raise RestaurantScheduleOpensBeforeClosesError()

        try:
            await self.repo.db_session.commit()
            await self.repo.db_session.refresh(restaurant_schedule)
            return restaurant_schedule
        except IntegrityError:
            await self.repo.db_session.rollback()
            raise RestaurantScheduleAlreadyExistsError()
        except Exception:
            await self.repo.db_session.rollback()
            raise
