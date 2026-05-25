from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger
from app.exceptions.restaurant import (
    RestaurantAlreadyExistsError,
    RestaurantNotFoundError,
    RestaurantScheduleAlreadyExistsError,
    RestaurantScheduleNotFoundError,
    RestaurantScheduleOpensBeforeClosesError,
)
from app.models.restaurant import MealPeriodEnum, Restaurant, RestaurantSchedule
from app.repositories.restaurant_repository import (
    RestaurantRepository,
    RestaurantScheduleRepository,
)
from app.schemas.restaurant_schemas import (
    RestaurantCreate,
    RestaurantScheduleCreate,
    RestaurantScheduleUpdate,
    RestaurantUpdate,
)

logger = get_logger(__name__)


class RestaurantService:
    def __init__(self, repo: RestaurantRepository):
        self.repo = repo

    async def create_restaurant(self, restaurant_data: RestaurantCreate) -> Restaurant:
        existing = await self.repo.get_by_name(restaurant_data.name)
        if existing:
            logger.warning(
                "Tentativa de criar restaurante duplicado: %s", restaurant_data.name
            )
            raise RestaurantAlreadyExistsError()

        try:
            restaurant = Restaurant(**restaurant_data.model_dump())
            await self.repo.create(restaurant)
            await self.repo.db_session.commit()
            logger.info(
                "Restaurante criado: %s (campus: %s)",
                restaurant.name,
                restaurant.campus.value,
            )
            return restaurant

        except IntegrityError:
            await self.repo.db_session.rollback()
            raise RestaurantAlreadyExistsError()

        except Exception:
            await self.repo.db_session.rollback()
            raise

    async def list_restaurants(self) -> list[Restaurant]:
        restaurants = await self.repo.get_all()
        return restaurants

    async def get_restaurant(self, public_id: UUID) -> Restaurant:
        restaurant = await self.repo.get_by_public_id(public_id)

        if not restaurant:
            logger.warning("Restaurante não encontrado: %s", public_id)
            raise RestaurantNotFoundError()

        return restaurant

    async def update_restaurant(
        self,
        public_id: UUID,
        restaurant_data: RestaurantUpdate,
    ) -> Restaurant:
        restaurant = await self.repo.get_by_public_id(public_id)

        if not restaurant:
            raise RestaurantNotFoundError()

        updated_data = restaurant_data.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        new_name = updated_data.get("name")

        if new_name and new_name != restaurant.name:
            existing = await self.repo.get_by_name(new_name)

            if existing:
                raise RestaurantAlreadyExistsError()

        for field, value in updated_data.items():
            setattr(
                restaurant,
                field,
                value,
            )

        try:
            await self.repo.db_session.commit()
            await self.repo.db_session.refresh(restaurant)
            return restaurant

        except IntegrityError:
            await self.repo.db_session.rollback()
            raise RestaurantAlreadyExistsError()

        except Exception:
            await self.repo.db_session.rollback()
            raise


class RestaurantScheduleService:
    def __init__(
        self,
        repo: RestaurantScheduleRepository,
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
            restaurant_schedules = await self.repo.list_by_ru_id_and_meal_period(
                restaurant.id, meal_period
            )
        else:
            restaurant_schedules = await self.repo.list_by_ru_id(restaurant.id)

        return restaurant_schedules

    async def update_restaurant_schedule(
        self,
        restaurant_public_id: UUID,
        restaurant_schedule_public_id: UUID,
        restaurant_schedule_data: RestaurantScheduleUpdate,
    ) -> RestaurantSchedule:
        restaurant = await self._get_restaurant_by_public_id_or_error(
            restaurant_public_id
        )

        restaurant_schedule = await self.repo.get_by_public_id(
            restaurant_schedule_public_id
        )

        if not restaurant_schedule:
            raise RestaurantScheduleNotFoundError()

        if restaurant.id != restaurant_schedule.ru_id:
            raise RestaurantScheduleNotFoundError()

        updated_data = restaurant_schedule_data.model_dump(
            exclude_none=True, exclude_unset=True
        )

        for field, value in updated_data.items():
            setattr(
                restaurant_schedule,
                field,
                value,
            )
        
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
