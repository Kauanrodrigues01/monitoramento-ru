from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.exception_handlers import (
    app_exception_handler,
    rate_limit_exceeded_handler,
)
from app.core.logging import get_logger, setup_logging
from app.core.rate_limiter import limiter
from app.core.settings import settings
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
    {
        "name": "Queue Snapshots",
        "description": (
            "Status atual estimado da fila para cada restaurante e período de refeição, "
            "calculado a partir dos relatórios recentes e do horário de funcionamento.\n\n"
        ),
    }
]

app = FastAPI(
    title="Monitoramento RU API",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=_TAGS_METADATA,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)

app.state.limiter = limiter

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.include_router(api_router)
