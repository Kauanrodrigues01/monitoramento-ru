from fastapi import APIRouter
from .endpoints.restaurants import router as restaurants_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(restaurants_router)
