from app.tests.factories.models.base.restaurant_base_model_factory import (
    BaseRestaurantAurorasFactory,
    BaseRestaurantFactory,
    BaseRestaurantLiberdadeFactory,
    BaseRestaurantPalmaresFactory,
    BaseRestaurantScheduleExceptionFactory,
    BaseRestaurantScheduleFactory,
)


class RestaurantDBFactory(BaseRestaurantFactory):
    pass


class RestaurantPalmaresDBFactory(
    BaseRestaurantPalmaresFactory,
    RestaurantDBFactory,
):
    pass


class RestaurantAurorasDBFactory(
    BaseRestaurantAurorasFactory,
    RestaurantDBFactory,
):
    pass


class RestaurantLiberdadeDBFactory(
    BaseRestaurantLiberdadeFactory,
    RestaurantDBFactory,
):
    pass


class RestaurantScheduleDBFactory(BaseRestaurantScheduleFactory):
    pass


class RestaurantScheduleExceptionDBFactory(BaseRestaurantScheduleExceptionFactory):
    pass
