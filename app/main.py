import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.exception_handlers import (
    app_exception_handler,
    rate_limit_exceeded_handler,
)
from app.core.logging import get_logger, setup_logging
from app.core.observability.prometheus import setup_prometheus
from app.core.pubsub import start_pubsub_listener
from app.core.rate_limiter import limiter
from app.core.redis import close_redis, get_redis
from app.core.settings import settings
from app.dependencies.database import DBSessionDep
from app.exceptions.base import AppException

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup")
    listener_task = asyncio.create_task(start_pubsub_listener())
    yield
    listener_task.cancel()
    await close_redis()
    logger.info("Application shutdown")


_TAGS_METADATA = [
    {
        "name": "Restaurants",
        "description": ("Restaurantes Universitários cadastrados no sistema.\n\n"),
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
    },
    {
        "name": "Metrics",
        "description": "Métricas agregadas do sistema para uso em dashboards.\n\n",
    },
]

app = FastAPI(
    title="Monitoramento RU API",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=_TAGS_METADATA,
)

setup_prometheus(app)

# =====================================
# Middlewares
# =====================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-Admin-Key", "X-Device-ID"],
)


@app.middleware("http")
async def log_request_body(request: Request, call_next):
    body = await request.body()

    logger.info(
        "method=%s path=%s body=%s",
        request.method,
        request.url.path,
        body.decode("utf-8"),
    )

    response = await call_next(request)

    return response


# =====================================
# Rate Limiter
# =====================================
app.state.limiter = limiter

# =====================================
# Exception Handlers
# =====================================
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# =====================================
# Routers
# =====================================
app.include_router(api_router)


@app.get(
    "/health/live",
    description="Endpoint que garante que a aplicação está rodando (liveness probe)",
    tags=["Health"],
)
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get(
    "/health/ready",
    description="Endpoint que verifica se a aplicação está pronta para receber requisições, verificando conexões com banco de dados e Redis (readiness probe)",
    tags=["Health"],
)
async def readiness(db_session: DBSessionDep):
    await db_session.execute(text("SELECT 1"))

    redis = await get_redis()
    await redis.ping()

    return {"status": "ready"}
