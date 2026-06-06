from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.restaurant import ExceptionTypeEnum, MealPeriodEnum
from app.schemas.restaurant_schedule_exception_schemas import (
    ActiveScheduleExceptionResponse,
    RestaurantScheduleExceptionResponse,
)
from app.tests.factories.schemas.restaurant_schema_factory import (
    build_restaurant_schedule_exception_create_schema,
    build_restaurant_schedule_exception_update_schema,
)


def _build_exception_response_payload(**kwargs) -> dict:
    now = datetime.now(UTC)
    data = {
        "public_id": uuid4(),
        "exception_date": date(2025, 12, 25),
        "exception_type": ExceptionTypeEnum.CLOSED,
        "meal_period": None,
        "opens_at": None,
        "closes_at": None,
        "reason": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(kwargs)
    return data


class TestRestaurantScheduleExceptionCreateSchema:
    def test_should_create_closed_exception_with_valid_data(self):
        data = build_restaurant_schedule_exception_create_schema()

        assert data.exception_date == date(2025, 12, 25)
        assert data.exception_type == ExceptionTypeEnum.CLOSED
        assert data.meal_period is None
        assert data.opens_at is None
        assert data.closes_at is None
        assert data.reason is None

    def test_should_create_custom_hours_exception_with_valid_data(self):
        data = build_restaurant_schedule_exception_create_schema(
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )

        assert data.exception_type == ExceptionTypeEnum.CUSTOM_HOURS
        assert data.opens_at == time(11, 0)
        assert data.closes_at == time(14, 0)

    def test_should_default_meal_period_to_none(self):
        data = build_restaurant_schedule_exception_create_schema()

        assert data.meal_period is None

    def test_should_default_opens_at_to_none(self):
        data = build_restaurant_schedule_exception_create_schema()

        assert data.opens_at is None

    def test_should_default_closes_at_to_none(self):
        data = build_restaurant_schedule_exception_create_schema()

        assert data.closes_at is None

    def test_should_default_reason_to_none(self):
        data = build_restaurant_schedule_exception_create_schema()

        assert data.reason is None

    def test_should_reject_when_exception_date_is_missing(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(exception_date=None)

    def test_should_reject_when_exception_type_is_missing(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(exception_type=None)

    def test_should_reject_invalid_exception_type(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(exception_type="HOLIDAY")

    def test_should_reject_invalid_meal_period(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(meal_period="BREAKFAST")

    def test_should_accept_meal_period_with_closed_type(self):
        data = build_restaurant_schedule_exception_create_schema(
            exception_type=ExceptionTypeEnum.CLOSED,
            meal_period=MealPeriodEnum.LUNCH,
        )

        assert data.meal_period == MealPeriodEnum.LUNCH

    def test_should_accept_meal_period_with_custom_hours_type(self):
        data = build_restaurant_schedule_exception_create_schema(
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            meal_period=MealPeriodEnum.DINNER,
            opens_at=time(17, 0),
            closes_at=time(19, 0),
        )

        assert data.meal_period == MealPeriodEnum.DINNER

    def test_should_reject_custom_hours_without_opens_at(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(
                exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
                closes_at=time(14, 0),
            )

    def test_should_reject_custom_hours_without_closes_at(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(
                exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
                opens_at=time(11, 0),
            )

    def test_should_reject_custom_hours_without_any_times(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(
                exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            )

    def test_should_reject_custom_hours_when_opens_at_equals_closes_at(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(
                exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
                opens_at=time(11, 0),
                closes_at=time(11, 0),
            )

    def test_should_reject_custom_hours_when_opens_at_after_closes_at(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(
                exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
                opens_at=time(15, 0),
                closes_at=time(11, 0),
            )

    def test_should_accept_custom_hours_with_valid_time_range(self):
        data = build_restaurant_schedule_exception_create_schema(
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(17, 0),
            closes_at=time(19, 0),
        )

        assert data.opens_at == time(17, 0)
        assert data.closes_at == time(19, 0)

    def test_should_reject_closed_with_opens_at(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(
                exception_type=ExceptionTypeEnum.CLOSED,
                opens_at=time(11, 0),
            )

    def test_should_reject_closed_with_closes_at(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(
                exception_type=ExceptionTypeEnum.CLOSED,
                closes_at=time(14, 0),
            )

    def test_should_reject_closed_with_both_times(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(
                exception_type=ExceptionTypeEnum.CLOSED,
                opens_at=time(11, 0),
                closes_at=time(14, 0),
            )

    def test_should_accept_reason_for_closed_type(self):
        data = build_restaurant_schedule_exception_create_schema(
            reason="Feriado nacional",
        )

        assert data.reason == "Feriado nacional"

    def test_should_accept_reason_for_custom_hours_type(self):
        data = build_restaurant_schedule_exception_create_schema(
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
            reason="Horário reduzido",
        )

        assert data.reason == "Horário reduzido"

    def test_should_reject_reason_above_max_length(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_create_schema(reason="x" * 256)

    def test_should_accept_reason_at_max_length(self):
        data = build_restaurant_schedule_exception_create_schema(reason="x" * 255)

        assert len(data.reason) == 255


class TestRestaurantScheduleExceptionUpdateSchema:
    def test_should_accept_empty_payload(self):
        data = build_restaurant_schedule_exception_update_schema()

        assert data.model_dump(exclude_unset=True) == {}

    def test_should_accept_only_exception_type(self):
        data = build_restaurant_schedule_exception_update_schema(
            exception_type=ExceptionTypeEnum.CLOSED,
        )

        assert data.exception_type == ExceptionTypeEnum.CLOSED

    def test_should_accept_only_meal_period(self):
        data = build_restaurant_schedule_exception_update_schema(
            meal_period=MealPeriodEnum.LUNCH,
        )

        assert data.meal_period == MealPeriodEnum.LUNCH

    def test_should_accept_only_opens_at(self):
        data = build_restaurant_schedule_exception_update_schema(opens_at=time(10, 0))

        assert data.opens_at == time(10, 0)

    def test_should_accept_only_closes_at(self):
        data = build_restaurant_schedule_exception_update_schema(closes_at=time(15, 0))

        assert data.closes_at == time(15, 0)

    def test_should_accept_only_reason(self):
        data = build_restaurant_schedule_exception_update_schema(reason="Greve")

        assert data.reason == "Greve"

    def test_should_accept_exception_type_none(self):
        data = build_restaurant_schedule_exception_update_schema(exception_type=None)

        assert data.exception_type is None

    def test_should_accept_meal_period_none(self):
        data = build_restaurant_schedule_exception_update_schema(meal_period=None)

        assert data.meal_period is None

    def test_should_accept_opens_at_none(self):
        data = build_restaurant_schedule_exception_update_schema(opens_at=None)

        assert data.opens_at is None

    def test_should_accept_closes_at_none(self):
        data = build_restaurant_schedule_exception_update_schema(closes_at=None)

        assert data.closes_at is None

    def test_should_accept_reason_none(self):
        data = build_restaurant_schedule_exception_update_schema(reason=None)

        assert data.reason is None

    def test_should_reject_invalid_exception_type(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_update_schema(exception_type="HOLIDAY")

    def test_should_reject_invalid_meal_period(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_update_schema(meal_period="BREAKFAST")

    def test_should_reject_reason_above_max_length(self):
        with pytest.raises(ValidationError):
            build_restaurant_schedule_exception_update_schema(reason="x" * 256)

    def test_should_accept_reason_at_max_length(self):
        data = build_restaurant_schedule_exception_update_schema(reason="x" * 255)

        assert len(data.reason) == 255

    def test_should_exclude_unset_fields_from_dump(self):
        data = build_restaurant_schedule_exception_update_schema(reason="Greve")

        dump = data.model_dump(exclude_unset=True)

        assert "reason" in dump
        assert "exception_type" not in dump
        assert "meal_period" not in dump
        assert "opens_at" not in dump
        assert "closes_at" not in dump

    def test_should_accept_custom_hours_exception_type(self):
        data = build_restaurant_schedule_exception_update_schema(
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
        )

        assert data.exception_type == ExceptionTypeEnum.CUSTOM_HOURS

    def test_should_include_all_set_fields_in_dump(self):
        data = build_restaurant_schedule_exception_update_schema(
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )

        dump = data.model_dump(exclude_unset=True)

        assert dump == {
            "exception_type": ExceptionTypeEnum.CUSTOM_HOURS,
            "opens_at": time(11, 0),
            "closes_at": time(14, 0),
        }


class TestRestaurantScheduleExceptionResponseSchema:
    def test_should_validate_from_dict_with_closed_type(self):
        payload = _build_exception_response_payload()

        data = RestaurantScheduleExceptionResponse(**payload)

        assert data.public_id == payload["public_id"]
        assert data.exception_date == payload["exception_date"]
        assert data.exception_type == ExceptionTypeEnum.CLOSED
        assert data.meal_period is None
        assert data.opens_at is None
        assert data.closes_at is None
        assert data.reason is None

    def test_should_validate_from_dict_with_custom_hours_type(self):
        payload = _build_exception_response_payload(
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )

        data = RestaurantScheduleExceptionResponse(**payload)

        assert data.exception_type == ExceptionTypeEnum.CUSTOM_HOURS
        assert data.opens_at == time(11, 0)
        assert data.closes_at == time(14, 0)

    def test_should_validate_from_orm_object(self):
        payload = _build_exception_response_payload()
        orm_obj = SimpleNamespace(**payload)

        data = RestaurantScheduleExceptionResponse.model_validate(orm_obj)

        assert data.public_id == payload["public_id"]
        assert data.exception_date == payload["exception_date"]
        assert data.exception_type == payload["exception_type"]

    def test_should_not_expose_internal_id(self):
        payload = _build_exception_response_payload()
        payload["id"] = 999

        data = RestaurantScheduleExceptionResponse(**payload)

        assert "id" not in data.model_dump()

    def test_should_not_expose_ru_id(self):
        payload = _build_exception_response_payload()
        payload["ru_id"] = 1

        data = RestaurantScheduleExceptionResponse(**payload)

        assert "ru_id" not in data.model_dump()

    def test_should_accept_null_meal_period(self):
        payload = _build_exception_response_payload(meal_period=None)

        data = RestaurantScheduleExceptionResponse(**payload)

        assert data.meal_period is None

    def test_should_accept_meal_period_lunch(self):
        payload = _build_exception_response_payload(meal_period=MealPeriodEnum.LUNCH)

        data = RestaurantScheduleExceptionResponse(**payload)

        assert data.meal_period == MealPeriodEnum.LUNCH

    def test_should_accept_null_opens_at(self):
        payload = _build_exception_response_payload(opens_at=None)

        data = RestaurantScheduleExceptionResponse(**payload)

        assert data.opens_at is None

    def test_should_accept_null_closes_at(self):
        payload = _build_exception_response_payload(closes_at=None)

        data = RestaurantScheduleExceptionResponse(**payload)

        assert data.closes_at is None

    def test_should_accept_null_reason(self):
        payload = _build_exception_response_payload(reason=None)

        data = RestaurantScheduleExceptionResponse(**payload)

        assert data.reason is None

    def test_should_accept_reason_with_value(self):
        payload = _build_exception_response_payload(reason="Feriado nacional")

        data = RestaurantScheduleExceptionResponse(**payload)

        assert data.reason == "Feriado nacional"

    def test_should_validate_from_orm_object_with_custom_hours_type(self):
        payload = _build_exception_response_payload(
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        orm_obj = SimpleNamespace(**payload)

        data = RestaurantScheduleExceptionResponse.model_validate(orm_obj)

        assert data.exception_type == ExceptionTypeEnum.CUSTOM_HOURS
        assert data.opens_at == time(11, 0)
        assert data.closes_at == time(14, 0)

    def test_should_expose_all_expected_fields_in_dump(self):
        payload = _build_exception_response_payload()

        data = RestaurantScheduleExceptionResponse(**payload)
        dump = data.model_dump()

        expected_fields = {
            "public_id",
            "exception_date",
            "exception_type",
            "meal_period",
            "opens_at",
            "closes_at",
            "reason",
            "created_at",
            "updated_at",
        }
        assert set(dump.keys()) == expected_fields


class TestActiveScheduleExceptionResponseSchema:
    def test_should_accept_exception_none(self):
        data = ActiveScheduleExceptionResponse(exception=None)

        assert data.exception is None

    def test_should_accept_exception_with_value(self):
        payload = _build_exception_response_payload()
        inner = RestaurantScheduleExceptionResponse(**payload)

        data = ActiveScheduleExceptionResponse(exception=inner)

        assert data.exception is inner

    def test_model_dump_has_only_exception_key(self):
        data = ActiveScheduleExceptionResponse(exception=None)
        dump = data.model_dump()

        assert set(dump.keys()) == {"exception"}

    def test_should_validate_from_dict_with_none(self):
        data = ActiveScheduleExceptionResponse(**{"exception": None})

        assert data.exception is None

    def test_should_validate_from_dict_with_exception_object(self):
        payload = _build_exception_response_payload(
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(10, 0),
            closes_at=time(13, 0),
            meal_period=MealPeriodEnum.LUNCH,
        )
        data = ActiveScheduleExceptionResponse(
            exception=RestaurantScheduleExceptionResponse(**payload)
        )

        assert data.exception is not None
        assert data.exception.exception_type == ExceptionTypeEnum.CUSTOM_HOURS
        assert data.exception.meal_period == MealPeriodEnum.LUNCH
