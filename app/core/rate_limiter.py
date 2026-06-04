from fastapi import Request
from slowapi import Limiter

from app.core.settings import settings
from app.services.ip_service import IpService


def rate_limit_key(request: Request) -> str:
    device_id = request.headers.get("X-Device-ID")

    if device_id:
        return f"device:{device_id}"

    client_ip = IpService.get_client_ip(request)

    if client_ip:
        return f"ip:{client_ip}"

    return "anonymous"


limiter = Limiter(
    key_func=rate_limit_key,
    storage_uri=settings.REDIS_URL,  # None → MemoryStorage (single-worker only)
)
