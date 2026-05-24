from app.models.restaurant import CampusEnum
from app.schemas.restaurant_schemas import RestaurantCreate, RestaurantUpdate


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
