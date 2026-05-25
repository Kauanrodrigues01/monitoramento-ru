from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import MealPeriodEnum, RestaurantSchedule


class RestaurantScheduleRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(
        self, restaurant_schedule: RestaurantSchedule
    ) -> RestaurantSchedule:
        self.db_session.add(restaurant_schedule)
        await self.db_session.flush()
        await self.db_session.refresh(restaurant_schedule)
        return restaurant_schedule

    async def get_by_public_id(
        self, public_id: UUID, only_active: bool = True
    ) -> RestaurantSchedule | None:
        query = select(RestaurantSchedule).where(
            RestaurantSchedule.public_id == public_id
        )
        if only_active:
            query = query.where(RestaurantSchedule.is_active.is_(True))
        result = await self.db_session.scalar(query)
        return result

    async def list_by_ru_id(
        self, ru_id: int, only_active: bool = True
    ) -> list[RestaurantSchedule]:
        query = select(RestaurantSchedule).where(RestaurantSchedule.ru_id == ru_id)
        if only_active:
            query = query.where(RestaurantSchedule.is_active.is_(True))
        result = await self.db_session.scalars(query)
        return list(result)

    async def list_by_ru_id_and_meal_period(
        self, ru_id: int, meal_period: MealPeriodEnum, only_active: bool = True
    ) -> list[RestaurantSchedule]:
        query = select(RestaurantSchedule).where(
            RestaurantSchedule.ru_id == ru_id,
            RestaurantSchedule.meal_period == meal_period,
        )
        if only_active:
            query = query.where(RestaurantSchedule.is_active.is_(True))
        result = await self.db_session.scalars(query)
        return list(result)

    async def list_by_ru_id_and_weekday(
        self, ru_id: int, weekday: int, only_active: bool = True
    ) -> list[RestaurantSchedule]:
        query = select(RestaurantSchedule).where(
            RestaurantSchedule.ru_id == ru_id,
            RestaurantSchedule.weekday == weekday,
        )
        if only_active:
            query = query.where(RestaurantSchedule.is_active.is_(True))
        result = await self.db_session.scalars(query)
        return list(result)

    async def get_by_ru_id_weekday_and_meal_period(
        self,
        ru_id: int,
        weekday: int,
        meal_period: MealPeriodEnum,
        only_active: bool = True,
    ) -> RestaurantSchedule | None:
        query = select(RestaurantSchedule).where(
            RestaurantSchedule.ru_id == ru_id,
            RestaurantSchedule.weekday == weekday,
            RestaurantSchedule.meal_period == meal_period,
        )
        if only_active:
            query = query.where(RestaurantSchedule.is_active.is_(True))
        result = await self.db_session.scalar(query)
        return result
