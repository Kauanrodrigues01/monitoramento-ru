from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.exception_handlers import app_exception_handler
from app.core.logging import get_logger, setup_logging
from app.exceptions.base import AppException

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


app = FastAPI(title="Monitoramento RU API", version="1.0.0", lifespan=lifespan)

app.add_exception_handler(AppException, app_exception_handler)

app.include_router(api_router)
