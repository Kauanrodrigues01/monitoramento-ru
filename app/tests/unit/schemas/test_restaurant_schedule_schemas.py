from datetime import UTC, datetime, time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.restaurant import MealPeriodEnum
from app.schemas.restaurant_schedule_schemas import RestaurantScheduleResponse
from app.tests.factories.schemas.restaurant_schema_factory import (
    build_restaurant_schedule_create_schema,
    build_restaurant_schedule_update_schema,
)


def _build_restaurant_schedule_response_payload() -> dict:
    now = datetime.now(UTC)
    return {
        "public_id": uuid4(),
        "weekday": 0,
        "meal_period": MealPeriodEnum.LUNCH,
        "opens_at": time(11, 0),
        "closes_at": time(14, 0),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


class TestRestaurantScheduleCreateSchema:
    def test_should_create_with_valid_data(self):
        data = build_restaurant_schedule_create_schema()

        assert data.weekday == 0
        assert data.meal_period == MealPeriodEnum.LUNCH
        assert data.opens_at == time(11, 0)
        assert data.closes_at == time(14, 0)
        assert data.is_active is True

    def test_should_default_is_active_to_true(self):
        data = build_restaurant_schedule_create_schema()

        assert data.is_active is True

    def test_should_reject_weekday_above_max_limit(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_create_schema(weekday=6)

    def test_should_reject_weekday_below_min_limit(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_create_schema(weekday=-1)

    def test_should_accept_weekday_boundary_values(self):
        data_min = build_restaurant_schedule_create_schema(weekday=0)
        data_max = build_restaurant_schedule_create_schema(weekday=5)

        assert data_min.weekday == 0
        assert data_max.weekday == 5

    def test_should_reject_when_opens_at_equals_closes_at(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_create_schema(
                opens_at=time(11, 0),
                closes_at=time(11, 0),
            )

    def test_should_reject_when_opens_at_after_closes_at(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_create_schema(
                opens_at=time(15, 0),
                closes_at=time(11, 0),
            )

    def test_should_accept_valid_time_range(self):
        data = build_restaurant_schedule_create_schema(
            opens_at=time(17, 0),
            closes_at=time(19, 0),
        )

        assert data.opens_at == time(17, 0)
        assert data.closes_at == time(19, 0)

    def test_should_accept_dinner_meal_period(self):
        data = build_restaurant_schedule_create_schema(
            meal_period=MealPeriodEnum.DINNER
        )

        assert data.meal_period == MealPeriodEnum.DINNER

    def test_should_reject_invalid_meal_period(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_create_schema(meal_period="BREAKFAST")

    def test_should_reject_when_weekday_is_missing(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_create_schema(weekday=None)

    def test_should_reject_when_meal_period_is_missing(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_create_schema(meal_period=None)

    def test_should_reject_when_opens_at_is_missing(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_create_schema(opens_at=None)

    def test_should_reject_when_closes_at_is_missing(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_create_schema(closes_at=None)

    def test_should_accept_is_active_false(self):
        data = build_restaurant_schedule_create_schema(is_active=False)

        assert data.is_active is False


class TestRestaurantScheduleUpdateSchema:
    def test_should_accept_empty_payload(self):
        data = build_restaurant_schedule_update_schema()

        assert data.model_dump(exclude_unset=True) == {}

    def test_should_accept_partial_update_with_only_opens_at(self):
        data = build_restaurant_schedule_update_schema(opens_at=time(10, 0))

        assert data.opens_at == time(10, 0)
        assert data.closes_at is None

    def test_should_accept_partial_update_with_only_closes_at(self):
        data = build_restaurant_schedule_update_schema(closes_at=time(15, 0))

        assert data.closes_at == time(15, 0)
        assert data.opens_at is None

    def test_should_reject_when_both_times_provided_and_opens_at_after_closes_at(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_update_schema(
                opens_at=time(15, 0),
                closes_at=time(11, 0),
            )

    def test_should_reject_when_both_times_provided_and_equal(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_update_schema(
                opens_at=time(11, 0),
                closes_at=time(11, 0),
            )

    def test_should_accept_valid_time_range_when_both_provided(self):
        data = build_restaurant_schedule_update_schema(
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )

        assert data.opens_at == time(11, 0)
        assert data.closes_at == time(14, 0)

    def test_should_accept_weekday_none(self):
        data = build_restaurant_schedule_update_schema(weekday=None)

        assert data.weekday is None

    def test_should_reject_weekday_above_max_limit(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_update_schema(weekday=6)

    def test_should_reject_weekday_below_min_limit(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_update_schema(weekday=-1)

    def test_should_accept_is_active_none(self):
        data = build_restaurant_schedule_update_schema(is_active=None)

        assert data.is_active is None

    def test_should_accept_meal_period_none(self):
        data = build_restaurant_schedule_update_schema(meal_period=None)

        assert data.meal_period is None

    def test_should_reject_invalid_meal_period(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_update_schema(meal_period="BREAKFAST")

    def test_should_accept_weekday_boundary_values(self):
        data_min = build_restaurant_schedule_update_schema(weekday=0)
        data_max = build_restaurant_schedule_update_schema(weekday=5)

        assert data_min.weekday == 0
        assert data_max.weekday == 5

    def test_should_exclude_unset_fields_from_dump(self):
        data = build_restaurant_schedule_update_schema(opens_at=time(10, 0))

        dump = data.model_dump(exclude_unset=True)

        assert "opens_at" in dump
        assert "closes_at" not in dump
        assert "weekday" not in dump
        assert "meal_period" not in dump
        assert "is_active" not in dump

    def test_should_include_all_set_fields_in_dump(self):
        data = build_restaurant_schedule_update_schema(
            weekday=2,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )

        dump = data.model_dump(exclude_unset=True)

        assert dump == {"weekday": 2, "opens_at": time(11, 0), "closes_at": time(14, 0)}


class TestRestaurantScheduleResponseSchema:
    def test_should_validate_from_dict(self):
        payload = _build_restaurant_schedule_response_payload()

        data = RestaurantScheduleResponse(**payload)

        assert data.public_id == payload["public_id"]
        assert data.weekday == payload["weekday"]
        assert data.meal_period == payload["meal_period"]
        assert data.opens_at == payload["opens_at"]
        assert data.closes_at == payload["closes_at"]
        assert data.is_active == payload["is_active"]

    def test_should_validate_from_orm_object(self):
        payload = _build_restaurant_schedule_response_payload()
        schedule_obj = SimpleNamespace(**payload)

        data = RestaurantScheduleResponse.model_validate(schedule_obj)

        assert data.public_id == payload["public_id"]
        assert data.weekday == payload["weekday"]
        assert data.meal_period == payload["meal_period"]

    def test_should_not_expose_internal_id(self):
        payload = _build_restaurant_schedule_response_payload()
        payload["id"] = 999

        data = RestaurantScheduleResponse(**payload)

        assert "id" not in data.model_dump()

    def test_should_not_expose_ru_id(self):
        payload = _build_restaurant_schedule_response_payload()
        payload["ru_id"] = 1

        data = RestaurantScheduleResponse(**payload)

        assert "ru_id" not in data.model_dump()
