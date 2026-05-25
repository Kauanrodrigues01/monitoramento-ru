from datetime import date, datetime, time
from decimal import Decimal
from uuid import uuid4

import factory

from app.models.restaurant import (
    CampusEnum,
    ExceptionTypeEnum,
    MealPeriodEnum,
    Restaurant,
    RestaurantSchedule,
    RestaurantScheduleException,
)


class RestaurantFactory(factory.Factory):
    """Factory para criar instâncias de Restaurant para testes"""

    class Meta:
        model = Restaurant

    id = factory.Sequence(lambda n: n + 1)
    public_id = factory.LazyFunction(uuid4)
    name = factory.Sequence(lambda n: f"RU Campus {n}")
    campus = CampusEnum.PALMARES
    lat = Decimal("-4.215432")
    lng = Decimal("-38.727981")
    geofence_radius_m = 80
    is_active = True
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class RestaurantPalmaresFactory(RestaurantFactory):
    """Factory para RU Palmares"""

    name = "RU Palmares"
    campus = CampusEnum.PALMARES


class RestaurantAurorasFactory(RestaurantFactory):
    """Factory para RU Auroras"""

    name = "RU Auroras"
    campus = CampusEnum.AURORAS


class RestaurantLiberdadeFactory(RestaurantFactory):
    """Factory para RU Liberdade"""

    name = "RU Liberdade"
    campus = CampusEnum.LIBERDADE


class RestaurantScheduleFactory(factory.Factory):
    """Factory para criar instâncias de RestaurantSchedule para testes"""

    class Meta:
        model = RestaurantSchedule

    id = factory.Sequence(lambda n: n + 1)
    public_id = factory.LazyFunction(uuid4)
    ru_id = factory.Sequence(lambda n: n + 1)
    weekday = 0
    meal_period = MealPeriodEnum.LUNCH
    opens_at = time(11, 0)
    closes_at = time(14, 0)
    is_active = True
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class RestaurantScheduleExceptionFactory(factory.Factory):
    """Factory para criar instâncias de RestaurantScheduleException para testes"""

    class Meta:
        model = RestaurantScheduleException

    id = factory.Sequence(lambda n: n + 1)
    public_id = factory.LazyFunction(uuid4)
    ru_id = factory.Sequence(lambda n: n + 1)
    exception_date = date(2025, 12, 25)
    exception_type = ExceptionTypeEnum.CLOSED
    meal_period = None
    opens_at = None
    closes_at = None
    reason = None
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)
