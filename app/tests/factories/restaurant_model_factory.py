from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import factory

from app.models.restaurant import CampusEnum, Restaurant


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
