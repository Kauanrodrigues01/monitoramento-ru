from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue_snapshot import QueueSnapshot
from app.models.restaurant import MealPeriodEnum


class QueueSnapshotRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(self, queue_snapshot: QueueSnapshot):
        self.db_session.add(queue_snapshot)
        await self.db_session.flush()
        await self.db_session.refresh(queue_snapshot)
        return queue_snapshot

    async def get_by_ru_id_and_meal_period(
        self,
        ru_id: int,
        meal_period: MealPeriodEnum,
    ) -> QueueSnapshot | None:
        query = select(QueueSnapshot).where(
            QueueSnapshot.ru_id == ru_id,
            QueueSnapshot.meal_period == meal_period,
        )
        result = await self.db_session.scalar(query)
        return result

    async def get_bulk_by_ru_ids_and_meal_period(
        self,
        ru_ids: list[int],
        meal_period: MealPeriodEnum,
    ) -> list[QueueSnapshot]:
        query = select(QueueSnapshot).where(
            QueueSnapshot.ru_id.in_(ru_ids),
            QueueSnapshot.meal_period == meal_period,
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def list_all(self) -> list[QueueSnapshot]:
        """Retorna todos os snapshots (todos os restaurantes e períodos)."""
        result = await self.db_session.execute(select(QueueSnapshot))
        return result.scalars().all()
