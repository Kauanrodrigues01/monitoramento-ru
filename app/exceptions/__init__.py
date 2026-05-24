from app.exceptions.base import AppException
from app.exceptions.restaurant import (
    RestaurantAlreadyExistsError,
    RestaurantNotFoundError,
)

__all__ = [
    "AppException",
    "RestaurantAlreadyExistsError",
    "RestaurantNotFoundError",
]
