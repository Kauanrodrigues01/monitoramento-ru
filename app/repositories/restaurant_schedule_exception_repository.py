from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import MealPeriodEnum, RestaurantScheduleException


class RestaurantScheduleExceptionRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(
        self, exception: RestaurantScheduleException
    ) -> RestaurantScheduleException:
        self.db_session.add(exception)
        await self.db_session.flush()
        await self.db_session.refresh(exception)
        return exception

    async def get_by_public_id(self, public_id: UUID) -> RestaurantScheduleException | None:
        query = select(RestaurantScheduleException).where(
            RestaurantScheduleException.public_id == public_id
        )
        return await self.db_session.scalar(query)

    async def list_by_ru_id(self, ru_id: int) -> list[RestaurantScheduleException]:
        query = select(RestaurantScheduleException).where(
            RestaurantScheduleException.ru_id == ru_id
        )
        result = await self.db_session.scalars(query)
        return list(result)

    async def list_by_ru_id_and_date(
        self, ru_id: int, exception_date: date
    ) -> list[RestaurantScheduleException]:
        query = select(RestaurantScheduleException).where(
            RestaurantScheduleException.ru_id == ru_id,
            RestaurantScheduleException.exception_date == exception_date,
        )
        result = await self.db_session.scalars(query)
        return list(result)

    async def get_by_ru_id_date_and_meal_period(
        self,
        ru_id: int,
        exception_date: date,
        meal_period: MealPeriodEnum | None,
    ) -> RestaurantScheduleException | None:
        query = select(RestaurantScheduleException).where(
            RestaurantScheduleException.ru_id == ru_id,
            RestaurantScheduleException.exception_date == exception_date,
            RestaurantScheduleException.meal_period == meal_period,
        )
        return await self.db_session.scalar(query)
