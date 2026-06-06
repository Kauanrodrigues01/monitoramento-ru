from datetime import date, time
from decimal import Decimal

import factory

from app.models.restaurant import (
    CampusEnum,
    ExceptionTypeEnum,
    MealPeriodEnum,
    Restaurant,
    RestaurantSchedule,
    RestaurantScheduleException,
)


class BaseRestaurantFactory(factory.Factory):
    class Meta:
        model = Restaurant

    name = factory.Sequence(lambda n: f"RU Campus {n}")
    campus = factory.Iterator(CampusEnum)

    lat = Decimal("-4.215432")
    lng = Decimal("-38.727981")

    geofence_radius_m = 80
    is_active = True


class BaseRestaurantPalmaresFactory(BaseRestaurantFactory):
    name = "RU Palmares"
    campus = CampusEnum.PALMARES


class BaseRestaurantAurorasFactory(BaseRestaurantFactory):
    name = "RU Auroras"
    campus = CampusEnum.AURORAS


class BaseRestaurantLiberdadeFactory(BaseRestaurantFactory):
    name = "RU Liberdade"
    campus = CampusEnum.LIBERDADE


class BaseRestaurantScheduleFactory(factory.Factory):
    class Meta:
        model = RestaurantSchedule

    ru_id = 1

    weekday = 0

    meal_period = MealPeriodEnum.LUNCH

    opens_at = time(11, 0)
    closes_at = time(14, 0)

    is_active = True


class BaseRestaurantScheduleExceptionFactory(factory.Factory):
    class Meta:
        model = RestaurantScheduleException

    ru_id = 1

    exception_date = date(2025, 12, 25)

    exception_type = ExceptionTypeEnum.CLOSED

    meal_period = None

    opens_at = None
    closes_at = None

    reason = None
