from slowapi import Limiter

from app.core.settings import settings
from app.services.ip_service import IpService

limiter = Limiter(
    key_func=IpService.get_client_ip,
    storage_uri=settings.REDIS_URL,  # None → MemoryStorage (single-worker only)
)
