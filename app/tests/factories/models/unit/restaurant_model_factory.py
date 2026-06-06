from datetime import UTC, datetime
from uuid import uuid4

import factory

from app.tests.factories.models.base.restaurant_base_model_factory import (
    BaseRestaurantAurorasFactory,
    BaseRestaurantFactory,
    BaseRestaurantLiberdadeFactory,
    BaseRestaurantPalmaresFactory,
    BaseRestaurantScheduleExceptionFactory,
    BaseRestaurantScheduleFactory,
)


class RestaurantFactory(BaseRestaurantFactory):
    id = factory.Sequence(lambda n: n + 1)

    public_id = factory.LazyFunction(uuid4)

    created_at = factory.LazyFunction(lambda: datetime.now(UTC))

    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class RestaurantPalmaresFactory(
    BaseRestaurantPalmaresFactory,
    RestaurantFactory,
):
    pass


class RestaurantAurorasFactory(
    BaseRestaurantAurorasFactory,
    RestaurantFactory,
):
    pass


class RestaurantLiberdadeFactory(
    BaseRestaurantLiberdadeFactory,
    RestaurantFactory,
):
    pass


class RestaurantScheduleFactory(BaseRestaurantScheduleFactory):
    id = factory.Sequence(lambda n: n + 1)

    public_id = factory.LazyFunction(uuid4)

    ru_id = factory.Sequence(lambda n: n + 1)

    created_at = factory.LazyFunction(lambda: datetime.now(UTC))

    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class RestaurantScheduleExceptionFactory(BaseRestaurantScheduleExceptionFactory):
    id = factory.Sequence(lambda n: n + 1)

    public_id = factory.LazyFunction(uuid4)

    ru_id = factory.Sequence(lambda n: n + 1)

    created_at = factory.LazyFunction(lambda: datetime.now(UTC))

    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))
