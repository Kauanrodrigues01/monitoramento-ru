from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.queue_snapshot import SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.schemas.queue_snapshot_schemas import (
    QueueSnapshotBulkItem,
    QueueSnapshotOverride,
    QueueSnapshotResponse,
)
from app.tests.factories.queue_snapshot_schema_factory import (
    build_queue_snapshot_bulk_item,
)


def _build_response_payload(**kwargs) -> dict:
    data = {
        "meal_period": MealPeriodEnum.LUNCH,
        "current_status": SnapshotStatusEnum.NO_DATA,
        "reports_last_15m": 0,
        "last_report_at": None,
        "updated_at": datetime(2026, 5, 26, 11, 45, 0),
    }
    data.update(kwargs)
    return data


class TestQueueSnapshotOverrideSchema:
    def test_should_create_with_valid_data(self):
        data = QueueSnapshotOverride(
            current_status=SnapshotStatusEnum.LARGE,
            override_active=True,
        )

        assert data.current_status == SnapshotStatusEnum.LARGE
        assert data.override_active is True

    def test_should_accept_all_valid_statuses(self):
        for status in SnapshotStatusEnum:
            data = QueueSnapshotOverride(current_status=status, override_active=False)
            assert data.current_status == status

    def test_should_accept_override_active_false(self):
        data = QueueSnapshotOverride(
            current_status=SnapshotStatusEnum.SMALL,
            override_active=False,
        )

        assert data.override_active is False

    def test_should_reject_when_current_status_is_missing(self):
        with pytest.raises(ValidationError):
            QueueSnapshotOverride(override_active=True)

    def test_should_reject_when_override_active_is_missing(self):
        with pytest.raises(ValidationError):
            QueueSnapshotOverride(current_status=SnapshotStatusEnum.LARGE)

    def test_should_reject_invalid_current_status(self):
        with pytest.raises(ValidationError):
            QueueSnapshotOverride(current_status="CROWDED", override_active=True)

    def test_should_expose_all_expected_fields_in_dump(self):
        data = QueueSnapshotOverride(
            current_status=SnapshotStatusEnum.MEDIUM,
            override_active=True,
        )

        assert set(data.model_dump().keys()) == {"current_status", "override_active"}


class TestQueueSnapshotBulkItemSchema:
    def test_should_create_with_valid_data(self):
        data = build_queue_snapshot_bulk_item()

        assert data.meal_period == MealPeriodEnum.LUNCH
        assert data.current_status == SnapshotStatusEnum.NO_DATA
        assert data.reports_last_15m == 0
        assert data.last_report_at is None

    def test_should_accept_last_report_at_as_none(self):
        data = build_queue_snapshot_bulk_item(last_report_at=None)

        assert data.last_report_at is None

    def test_should_accept_last_report_at_as_datetime(self):
        dt = datetime(2026, 5, 26, 11, 0, 0)

        data = build_queue_snapshot_bulk_item(last_report_at=dt)

        assert data.last_report_at == dt

    def test_should_preserve_restaurant_public_id(self):
        public_id = uuid4()

        data = build_queue_snapshot_bulk_item(restaurant_public_id=public_id)

        assert data.restaurant_public_id == public_id

    def test_should_reject_invalid_restaurant_public_id(self):
        with pytest.raises(ValidationError):
            build_queue_snapshot_bulk_item(restaurant_public_id="not-a-uuid")

    def test_should_reject_when_restaurant_public_id_is_missing(self):
        with pytest.raises(ValidationError):
            QueueSnapshotBulkItem(
                meal_period=MealPeriodEnum.LUNCH,
                current_status=SnapshotStatusEnum.NO_DATA,
                reports_last_15m=0,
                last_report_at=None,
                updated_at=datetime(2026, 5, 26, 11, 45, 0),
            )

    def test_should_reject_when_meal_period_is_missing(self):
        with pytest.raises(ValidationError):
            build_queue_snapshot_bulk_item(meal_period=None)

    def test_should_reject_when_current_status_is_missing(self):
        with pytest.raises(ValidationError):
            build_queue_snapshot_bulk_item(current_status=None)

    def test_should_reject_when_reports_last_15m_is_missing(self):
        with pytest.raises(ValidationError):
            build_queue_snapshot_bulk_item(reports_last_15m=None)

    def test_should_reject_when_updated_at_is_missing(self):
        with pytest.raises(ValidationError):
            build_queue_snapshot_bulk_item(updated_at=None)

    def test_should_reject_invalid_meal_period(self):
        with pytest.raises(ValidationError):
            build_queue_snapshot_bulk_item(meal_period="BREAKFAST")

    def test_should_reject_invalid_current_status(self):
        with pytest.raises(ValidationError):
            build_queue_snapshot_bulk_item(current_status="CROWDED")

    def test_should_accept_all_valid_meal_periods(self):
        for period in MealPeriodEnum:
            data = build_queue_snapshot_bulk_item(meal_period=period)
            assert data.meal_period == period

    def test_should_accept_all_valid_statuses(self):
        for status in SnapshotStatusEnum:
            data = build_queue_snapshot_bulk_item(current_status=status)
            assert data.current_status == status

    def test_should_reject_when_last_report_at_is_missing(self):
        with pytest.raises(ValidationError):
            QueueSnapshotBulkItem(
                restaurant_public_id=uuid4(),
                meal_period=MealPeriodEnum.LUNCH,
                current_status=SnapshotStatusEnum.NO_DATA,
                reports_last_15m=0,
                updated_at=datetime(2026, 5, 26, 11, 45, 0),
            )

    def test_should_parse_restaurant_public_id_from_string(self):
        public_id = uuid4()

        data = build_queue_snapshot_bulk_item(restaurant_public_id=str(public_id))

        assert data.restaurant_public_id == public_id

    def test_should_expose_all_expected_fields_in_dump(self):
        data = build_queue_snapshot_bulk_item()

        expected_fields = {
            "restaurant_public_id",
            "meal_period",
            "current_status",
            "reports_last_15m",
            "last_report_at",
            "updated_at",
        }
        assert set(data.model_dump().keys()) == expected_fields


class TestQueueSnapshotResponseSchema:
    def test_should_validate_from_dict(self):
        payload = _build_response_payload()

        data = QueueSnapshotResponse(**payload)

        assert data.meal_period == MealPeriodEnum.LUNCH
        assert data.current_status == SnapshotStatusEnum.NO_DATA
        assert data.reports_last_15m == 0

    def test_should_validate_from_orm_object(self):
        payload = _build_response_payload(
            current_status=SnapshotStatusEnum.SMALL,
            reports_last_15m=5,
        )
        orm_obj = SimpleNamespace(**payload)

        data = QueueSnapshotResponse.model_validate(orm_obj)

        assert data.current_status == SnapshotStatusEnum.SMALL
        assert data.reports_last_15m == 5

    def test_should_accept_last_report_at_as_none(self):
        payload = _build_response_payload(last_report_at=None)

        data = QueueSnapshotResponse(**payload)

        assert data.last_report_at is None

    def test_should_accept_last_report_at_as_datetime(self):
        dt = datetime(2026, 5, 26, 12, 0, 0)
        payload = _build_response_payload(last_report_at=dt)

        data = QueueSnapshotResponse(**payload)

        assert data.last_report_at == dt

    def test_should_reject_when_meal_period_is_missing(self):
        payload = _build_response_payload()
        del payload["meal_period"]

        with pytest.raises(ValidationError):
            QueueSnapshotResponse(**payload)

    def test_should_reject_when_current_status_is_missing(self):
        payload = _build_response_payload()
        del payload["current_status"]

        with pytest.raises(ValidationError):
            QueueSnapshotResponse(**payload)

    def test_should_reject_when_reports_last_15m_is_missing(self):
        payload = _build_response_payload()
        del payload["reports_last_15m"]

        with pytest.raises(ValidationError):
            QueueSnapshotResponse(**payload)

    def test_should_reject_when_updated_at_is_missing(self):
        payload = _build_response_payload()
        del payload["updated_at"]

        with pytest.raises(ValidationError):
            QueueSnapshotResponse(**payload)

    def test_should_accept_all_valid_meal_periods(self):
        for period in MealPeriodEnum:
            payload = _build_response_payload(meal_period=period)
            data = QueueSnapshotResponse(**payload)
            assert data.meal_period == period

    def test_should_accept_all_valid_statuses(self):
        for status in SnapshotStatusEnum:
            payload = _build_response_payload(current_status=status)
            data = QueueSnapshotResponse(**payload)
            assert data.current_status == status

    def test_should_expose_all_expected_fields_in_dump(self):
        payload = _build_response_payload()

        data = QueueSnapshotResponse(**payload)

        expected_fields = {
            "meal_period",
            "current_status",
            "reports_last_15m",
            "last_report_at",
            "updated_at",
        }
        assert set(data.model_dump().keys()) == expected_fields

    def test_should_not_expose_confidence_score(self):
        payload = _build_response_payload()
        payload["confidence_score"] = "0.95"

        data = QueueSnapshotResponse(**payload)

        assert "confidence_score" not in data.model_dump()

    def test_should_not_expose_override_active(self):
        payload = _build_response_payload()
        payload["override_active"] = True

        data = QueueSnapshotResponse(**payload)

        assert "override_active" not in data.model_dump()

    def test_should_not_expose_ru_id(self):
        payload = _build_response_payload()
        payload["ru_id"] = 42

        data = QueueSnapshotResponse(**payload)

        assert "ru_id" not in data.model_dump()

    def test_should_reject_when_last_report_at_is_missing(self):
        payload = _build_response_payload()
        del payload["last_report_at"]

        with pytest.raises(ValidationError):
            QueueSnapshotResponse(**payload)

    def test_should_reject_invalid_meal_period(self):
        payload = _build_response_payload(meal_period="BREAKFAST")

        with pytest.raises(ValidationError):
            QueueSnapshotResponse(**payload)

    def test_should_reject_invalid_current_status(self):
        payload = _build_response_payload(current_status="CROWDED")

        with pytest.raises(ValidationError):
            QueueSnapshotResponse(**payload)

    def test_should_preserve_updated_at(self):
        expected = datetime(2026, 5, 26, 11, 45, 0)
        payload = _build_response_payload(updated_at=expected)

        data = QueueSnapshotResponse(**payload)

        assert data.updated_at == expected
