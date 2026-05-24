from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
