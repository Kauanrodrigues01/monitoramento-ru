from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import Restaurant


class RestaurantRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_by_public_id(self, public_id: UUID) -> Restaurant | None:
        query = select(Restaurant).where(Restaurant.public_id == public_id)
        result = await self.db_session.scalar(query)
        return result

    async def get_by_name(self, name: str) -> Restaurant | None:
        query = select(Restaurant).where(Restaurant.name == name)
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

    async def get_all(self) -> list[Restaurant]:
        result = await self.db_session.scalars(select(Restaurant))
        return list(result.all())
