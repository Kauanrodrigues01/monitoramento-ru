from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.restaurant import CampusEnum
from app.schemas.restaurant_schemas import RestaurantResponse
from app.tests.factories.schemas.restaurant_schema_factory import (
    build_restaurant_create_schema,
    build_restaurant_update_schema,
)


def _build_restaurant_response_payload() -> dict:
    now = datetime.now(UTC)
    return {
        "public_id": uuid4(),
        "name": "RU PALMARES",
        "campus": CampusEnum.PALMARES,
        "lat": Decimal("-4.215432"),
        "lng": Decimal("-38.727981"),
        "geofence_radius_m": 80,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


class TestRestaurantCreateSchema:
    def test_should_set_default_name_when_missing_in_create(self):
        data = build_restaurant_create_schema(campus=CampusEnum.AURORAS.value)

        assert data.name == f"RU {CampusEnum.AURORAS.value}"

    def test_should_keep_custom_name_in_create(self):
        restaurant_name = "Restaurante do Auroras"

        data = build_restaurant_create_schema(
            name=restaurant_name,
        )

        assert data.name == restaurant_name

    def test_should_truncate_coordinates_to_6_decimals_in_create(self):
        lat = "-23.587469"
        lng = "-46.769427"
        long_lat = lat + "123456"
        long_lng = lng + "123456"
        data = build_restaurant_create_schema(
            lat=long_lat,
            lng=long_lng,
        )

        assert data.lat == Decimal(lat)
        assert data.lng == Decimal(lng)

    def test_should_reject_geofence_above_max_limit_in_create(self):
        with pytest.raises(ValidationError):
            build_restaurant_create_schema(geofence_radius_m=121)

    def test_should_reject_geofence_below_min_limit_in_create(self):
        with pytest.raises(ValidationError):
            build_restaurant_create_schema(geofence_radius_m=-1)

    def test_should_reject_lat_above_max_limit_in_create(self):
        with pytest.raises(ValidationError):
            build_restaurant_create_schema(lat="91")

    def test_should_reject_lat_below_min_limit_in_create(self):
        with pytest.raises(ValidationError):
            build_restaurant_create_schema(lat="-91")

    def test_should_reject_lng_above_max_limit_in_create(self):
        with pytest.raises(ValidationError):
            build_restaurant_create_schema(lng="181")

    def test_should_reject_lng_below_min_limit_in_create(self):
        with pytest.raises(ValidationError):
            build_restaurant_create_schema(lng="-181")

    def test_should_reject_too_short_name_in_create(self):
        with pytest.raises(ValidationError):
            build_restaurant_create_schema(name="ru")

    def test_should_reject_too_long_name_in_create(self):
        with pytest.raises(ValidationError):
            build_restaurant_create_schema(name=("a" * 121))


class TestRestaurantUpdateSchema:
    def test_should_accept_empty_payload_in_update(self):
        data = build_restaurant_update_schema()
        assert data.model_dump(exclude_unset=True) == {}

    def test_should_accept_name_none_in_update(self):
        data = build_restaurant_update_schema(name=None)
        assert data.name is None

    def test_should_reject_too_short_name_in_update(self):
        with pytest.raises(ValidationError):
            build_restaurant_update_schema(name="ru")

    def test_should_reject_too_long_name_in_update(self):
        with pytest.raises(ValidationError):
            build_restaurant_update_schema(name=("a" * 121))

    def test_should_accept_campus_none_in_update(self):
        data = build_restaurant_update_schema(campus=None)
        assert data.campus is None

    def test_should_accept_lat_none_in_update(self):
        data = build_restaurant_update_schema(lat=None)
        assert data.lat is None

    def test_should_reject_lat_above_max_limit_in_update(self):
        with pytest.raises(ValidationError):
            build_restaurant_update_schema(lat="91")

    def test_should_reject_lat_below_min_limit_in_update(self):
        with pytest.raises(ValidationError):
            build_restaurant_update_schema(lat="-91")

    def test_should_accept_lng_none_in_update(self):
        data = build_restaurant_update_schema(lng=None)
        assert data.lng is None

    def test_should_reject_lng_above_max_limit_in_update(self):
        with pytest.raises(ValidationError):
            build_restaurant_update_schema(lng="181")

    def test_should_reject_lng_below_min_limit_in_update(self):
        with pytest.raises(ValidationError):
            build_restaurant_update_schema(lng="-181")

    def test_should_accept_geofence_none_in_update(self):
        data = build_restaurant_update_schema(geofence_radius_m=None)
        assert data.geofence_radius_m is None

    def test_should_reject_geofence_above_max_limit_in_update(self):
        with pytest.raises(ValidationError):
            build_restaurant_update_schema(geofence_radius_m=121)

    def test_should_reject_geofence_below_min_limit_in_update(self):
        with pytest.raises(ValidationError):
            build_restaurant_update_schema(geofence_radius_m=-1)

    def test_should_accept_is_active_none_in_update(self):
        data = build_restaurant_update_schema(is_active=None)
        assert data.is_active is None

    def test_should_truncate_coordinates_to_6_decimals_in_update(self):
        lat = "-23.587469"
        lng = "-46.769427"
        long_lat = lat + "123456"
        long_lng = lng + "123456"
        data = build_restaurant_update_schema(
            lat=long_lat,
            lng=long_lng,
        )

        assert data.lat == Decimal(lat)
        assert data.lng == Decimal(lng)

    def test_should_keep_coordinates_none_in_update(self):
        data = build_restaurant_update_schema(lat=None, lng=None)
        assert data.lat is None
        assert data.lng is None


class TestRestaurantResponseSchema:
    def test_should_validate_restaurant_response_from_dict(self):
        payload = _build_restaurant_response_payload()

        data = RestaurantResponse(**payload)

        assert data.public_id == payload["public_id"]
        assert data.name == payload["name"]
        assert data.campus == payload["campus"]
        assert data.lat == payload["lat"]
        assert data.lng == payload["lng"]
        assert data.geofence_radius_m == payload["geofence_radius_m"]
        assert data.is_active == payload["is_active"]

    def test_should_validate_restaurant_response_from_object(self):
        payload = _build_restaurant_response_payload()
        restaurant_obj = SimpleNamespace(**payload)

        data = RestaurantResponse.model_validate(restaurant_obj)

        assert data.public_id == payload["public_id"]
        assert data.name == payload["name"]
        assert data.campus == payload["campus"]

    def test_should_ignore_internal_id_in_restaurant_response_payload(self):
        payload = _build_restaurant_response_payload()
        payload["id"] = 999

        data = RestaurantResponse(**payload)

        assert "id" not in data.model_dump()
        assert not hasattr(data, "id")
