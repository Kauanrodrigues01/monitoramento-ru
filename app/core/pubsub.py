from app.core.redis import get_redis
from app.core.websocket_manager import manager


async def start_pubsub_listener() -> None:
    redis = await get_redis()

    pubsub = redis.pubsub()
    await pubsub.subscribe("snapshots")

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue

        payload: str = message["data"]

        await manager.broadcast(room="snapshots", payload=payload)
