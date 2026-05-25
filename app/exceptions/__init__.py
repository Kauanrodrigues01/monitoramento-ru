from app.exceptions.base import AppException
from app.exceptions.restaurant_exceptions import (
    RestaurantAlreadyExistsError,
    RestaurantNotFoundError,
)

__all__ = [
    "AppException",
    "RestaurantAlreadyExistsError",
    "RestaurantNotFoundError",
]
