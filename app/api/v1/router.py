from fastapi import APIRouter

from app.core.settings import settings

from .endpoints.queue_reports import router as queue_reports_router
from .endpoints.queue_snapshots import router as queue_snapshots_router
from .endpoints.restaurant_schedule_exceptions import (
    router as restaurant_schedule_exceptions_router,
)
from .endpoints.restaurant_schedules import router as restaurant_schedules_router
from .endpoints.restaurants import router as restaurants_router

api_router = APIRouter(prefix="/api/v1")

if settings.DEBUG:
    from .endpoints.debug import router as debug_router

    api_router.include_router(debug_router)

api_router.include_router(restaurants_router)
api_router.include_router(restaurant_schedules_router)
api_router.include_router(restaurant_schedule_exceptions_router)
api_router.include_router(queue_reports_router)
api_router.include_router(queue_snapshots_router)
