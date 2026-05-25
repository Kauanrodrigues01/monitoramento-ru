from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.logging import get_logger
from app.exceptions.base import AppException

logger = get_logger(__name__)

_RATE_LIMIT_DETAIL = "Muitas requisições. Tente novamente em alguns minutos."


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    if exc.status_code >= 500:
        logger.exception("Erro interno: %s", exc.detail)
    else:
        logger.warning(
            "Erro %s em %s: %s", exc.status_code, request.url.path, exc.detail
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    logger.warning("Rate limit atingido em %s", request.url.path)
    response = JSONResponse(status_code=429, content={"detail": _RATE_LIMIT_DETAIL})
    response.headers["Retry-After"] = str(getattr(exc, "retry_after", ""))
    return response
