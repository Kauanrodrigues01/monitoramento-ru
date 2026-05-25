from datetime import time

from app.models.restaurant import CampusEnum, ExceptionTypeEnum, MealPeriodEnum
from app.schemas.restaurant_schedule_exception_schemas import (
    RestaurantScheduleExceptionCreate,
    RestaurantScheduleExceptionUpdate,
)
from app.schemas.restaurant_schemas import RestaurantCreate, RestaurantUpdate
from app.schemas.restaurant_schedule_schemas import (
    RestaurantScheduleCreate,
    RestaurantScheduleUpdate,
)


def build_restaurant_create_schema(**kwargs) -> RestaurantCreate:
    data = {
        "campus": CampusEnum.PALMARES,
        "lat": "-4.215432",
        "lng": "-38.727981",
        "geofence_radius_m": 80,
        "is_active": True,
    }

    data.update(kwargs)

    return RestaurantCreate(**data)


def build_restaurant_update_schema(**kwargs) -> RestaurantUpdate:
    return RestaurantUpdate(**kwargs)


def build_restaurant_schedule_create_schema(**kwargs) -> RestaurantScheduleCreate:
    data = {
        "weekday": 0,
        "meal_period": MealPeriodEnum.LUNCH,
        "opens_at": time(11, 0),
        "closes_at": time(14, 0),
        "is_active": True,
    }

    data.update(kwargs)

    return RestaurantScheduleCreate(**data)


def build_restaurant_schedule_update_schema(**kwargs) -> RestaurantScheduleUpdate:
    return RestaurantScheduleUpdate(**kwargs)


def build_restaurant_schedule_exception_create_schema(
    **kwargs,
) -> RestaurantScheduleExceptionCreate:
    from datetime import date

    data: dict = {
        "exception_date": date(2025, 12, 25),
        "exception_type": ExceptionTypeEnum.CLOSED,
    }
    data.update(kwargs)
    return RestaurantScheduleExceptionCreate(**data)


def build_restaurant_schedule_exception_update_schema(
    **kwargs,
) -> RestaurantScheduleExceptionUpdate:
    return RestaurantScheduleExceptionUpdate(**kwargs)
