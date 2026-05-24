from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.exceptions.base import AppException

logger = get_logger(__name__)


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
