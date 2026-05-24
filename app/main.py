from contextlib import asynccontextmanager

from api.v1.router import api_router
from core.exception_handlers import app_exception_handler
from core.logging import get_logger, setup_logging
from exceptions.base import AppException
from fastapi import FastAPI

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
