from fastapi import APIRouter

from .endpoints.restaurant_schedule_exceptions import (
    router as restaurant_schedule_exceptions_router,
)
from .endpoints.restaurant_schedules import router as restaurant_schedules_router
from .endpoints.restaurants import router as restaurants_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(restaurants_router)
api_router.include_router(restaurant_schedules_router)
api_router.include_router(restaurant_schedule_exceptions_router)
