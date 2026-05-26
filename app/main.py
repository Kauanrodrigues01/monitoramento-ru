from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.exception_handlers import (
    app_exception_handler,
    rate_limit_exceeded_handler,
)
from app.core.logging import get_logger, setup_logging
from app.core.rate_limiter import limiter
from app.exceptions.base import AppException

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


_TAGS_METADATA = [
    {
        "name": "Restaurants",
        "description": (
            "Restaurantes Universitários cadastrados no sistema.\n\n"
        ),
    },
    {
        "name": "Restaurant Schedules",
        "description": (
            "Horários regulares de funcionamento por período de refeição (almoço/jantar).\n\n"
        ),
    },
    {
        "name": "Restaurant Schedule Exceptions",
        "description": (
            "Exceções pontuais que sobrescrevem o horário regular — "
            "feriados, fechamentos e horários especiais.\n\n"
        ),
    },
    {
        "name": "Queue Reports",
        "description": (
            "Relatos de situação da fila enviados por clientes. "
            "Requer geo-assinatura válida.\n\n"
        ),
    },
]

app = FastAPI(
    title="Monitoramento RU API",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=_TAGS_METADATA,
)

app.state.limiter = limiter

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.include_router(api_router)
