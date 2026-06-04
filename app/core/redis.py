import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.settings import settings

_redis_client: Redis | None = None

_DEFAULT_REDIS_URL = "redis://localhost:6379"


async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL or _DEFAULT_REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
