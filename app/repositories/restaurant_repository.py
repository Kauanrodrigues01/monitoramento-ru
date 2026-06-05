from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import Restaurant


class RestaurantRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def count_active(self) -> int:
        query = (
            select(func.count())
            .select_from(Restaurant)
            .where(Restaurant.is_active.is_(True))
        )
        result = await self.db_session.scalar(query)
        return result

    async def get_by_id(self, id: int) -> Restaurant | None:
        query = select(Restaurant).where(Restaurant.id == id)
        result = await self.db_session.scalar(query)
        return result

    async def get_by_public_id(
        self, public_id: UUID, only_active: bool = True
    ) -> Restaurant | None:
        query = select(Restaurant).where(Restaurant.public_id == public_id)
        if only_active:
            query = query.where(Restaurant.is_active.is_(True))
        result = await self.db_session.scalar(query)
        return result

    async def get_by_name(
        self, name: str, only_active: bool = True
    ) -> Restaurant | None:
        query = select(Restaurant).where(Restaurant.name == name)
        if only_active:
            query = query.where(Restaurant.is_active.is_(True))
        result = await self.db_session.scalar(query)
        return result

    async def create(
        self,
        restaurant: Restaurant,
    ) -> Restaurant:
        """
        Adiciona um restaurante à transação.
        Não realiza o commit, quem chama esse método é responsável pelo commit/rollback.
        """
        self.db_session.add(restaurant)
        # flush() envia as alterações pendentes para o banco, mas sem confirmar a transação,
        # permitindo acessar valores gerados pelo banco (ex: id, timestamps, defaults)
        await self.db_session.flush()
        await self.db_session.refresh(restaurant)
        return restaurant

    async def get_bulk_by_public_ids(
        self, public_ids: list[UUID], only_active: bool = True
    ) -> list[Restaurant]:
        query = select(Restaurant).where(Restaurant.public_id.in_(public_ids))
        if only_active:
            query = query.where(Restaurant.is_active.is_(True))
        result = await self.db_session.scalars(query)
        return list(result.all())

    async def get_all(self, only_active: bool = True) -> list[Restaurant]:
        query = select(Restaurant)
        if only_active:
            query = query.where(Restaurant.is_active.is_(True))
        result = await self.db_session.scalars(query)
        return list(result.all())
