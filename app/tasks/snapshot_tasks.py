import asyncio

from app.core.celery import celery_app
from app.core.database import AsyncSessionLocal
from app.dependencies.snapshot_status_dependencies import get_snapshot_status_service


@celery_app.task(
    name="snapshot_tasks.update_snapshot_status_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def update_restaurant_snapshot_status_task(
    ru_id: int,
) -> None:
    asyncio.run(_update_snapshot(ru_id))


async def _update_snapshot(
    ru_id: int,
) -> None:
    async with AsyncSessionLocal() as session:
        service = get_snapshot_status_service(db_session=session)

        await service.update_snapshot(ru_id=ru_id)
