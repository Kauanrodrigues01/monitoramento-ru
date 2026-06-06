from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.queue_reports import ReportStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.schemas.queue_report_schemas import QueueReportResponse, truncate_coordinate
from app.tests.factories.schemas.queue_report_schema_factory import (
    build_queue_report_create_schema,
)


def _build_report_response_payload(**kwargs) -> dict:
    data = {
        "public_id": uuid4(),
        "status": ReportStatusEnum.SMALL,
        "meal_period": MealPeriodEnum.LUNCH,
        "created_at": datetime.now(UTC),
    }
    data.update(kwargs)
    return data


class TestQueueReportCreateSchema:
    def test_should_create_with_valid_data(self):
        data = build_queue_report_create_schema()

        assert data.status == ReportStatusEnum.SMALL
        assert data.lat == Decimal("-3.747361")
        assert data.lng == Decimal("-38.523060")
        assert data.accuracy_m is None

    def test_should_default_accuracy_m_to_none(self):
        data = build_queue_report_create_schema()

        assert data.accuracy_m is None

    def test_should_accept_accuracy_m_with_value(self):
        data = build_queue_report_create_schema(accuracy_m="12.50")

        assert data.accuracy_m == Decimal("12.50")

    def test_should_accept_accuracy_m_at_zero(self):
        data = build_queue_report_create_schema(accuracy_m="0")

        assert data.accuracy_m == Decimal("0")

    def test_should_reject_when_status_is_missing(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(status=None)

    def test_should_reject_when_lat_is_missing(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(lat=None)

    def test_should_reject_when_lng_is_missing(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(lng=None)

    def test_should_reject_invalid_status(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(status="CROWDED")

    def test_should_accept_all_valid_statuses(self):
        for status in ReportStatusEnum:
            data = build_queue_report_create_schema(status=status)
            assert data.status == status

    def test_should_reject_lat_above_90(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(lat="90.000001")

    def test_should_reject_lat_below_minus_90(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(lat="-90.000001")

    def test_should_accept_lat_at_boundary_90(self):
        data = build_queue_report_create_schema(lat="90")

        assert data.lat == Decimal("90")

    def test_should_accept_lat_at_boundary_minus_90(self):
        data = build_queue_report_create_schema(lat="-90")

        assert data.lat == Decimal("-90")

    def test_should_reject_lng_above_180(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(lng="180.000001")

    def test_should_reject_lng_below_minus_180(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(lng="-180.000001")

    def test_should_accept_lng_at_boundary_180(self):
        data = build_queue_report_create_schema(lng="180")

        assert data.lng == Decimal("180")

    def test_should_accept_lng_at_boundary_minus_180(self):
        data = build_queue_report_create_schema(lng="-180")

        assert data.lng == Decimal("-180")

    def test_should_preserve_lat_precision_in_schema(self):
        # A truncagem foi movida para o service (após validação da assinatura geo).
        # O schema aceita e preserva a precisão original do cliente.
        data = build_queue_report_create_schema(lat="-3.7473619999")

        assert data.lat == Decimal("-3.7473619999")

    def test_should_preserve_lng_precision_in_schema(self):
        data = build_queue_report_create_schema(lng="-38.5230609999")

        assert data.lng == Decimal("-38.5230609999")


class TestTruncateCoordinate:
    def test_should_truncate_to_6_decimal_places(self):
        assert truncate_coordinate(Decimal("-3.7473619999")) == Decimal("-3.747361")

    def test_should_truncate_positive_using_round_down_not_round(self):
        # 1.9999999 truncado para baixo = 1.999999, não arredondado para 2.000000
        assert truncate_coordinate(Decimal("1.9999999")) == Decimal("1.999999")

    def test_should_truncate_negative_toward_zero_not_away(self):
        # ROUND_DOWN trunca em direção ao zero:
        # -1.9999999 → -1.999999 (em direção ao zero), não -2.000000 (afastando do zero)
        assert truncate_coordinate(Decimal("-1.9999999")) == Decimal("-1.999999")

    def test_should_preserve_value_already_at_6_decimal_places(self):
        assert truncate_coordinate(Decimal("-4.215623")) == Decimal("-4.215623")

    def test_should_reject_accuracy_m_below_zero(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(accuracy_m="-0.01")

    def test_should_default_is_mock_location_to_false(self):
        data = build_queue_report_create_schema()

        assert data.is_mock_location is False

    def test_should_accept_is_mock_location_true(self):
        data = build_queue_report_create_schema(is_mock_location=True)

        assert data.is_mock_location is True

    def test_should_accept_is_mock_location_false(self):
        data = build_queue_report_create_schema(is_mock_location=False)

        assert data.is_mock_location is False

    def test_should_accept_valid_geo_signature(self):
        valid_sig = "b" * 64
        data = build_queue_report_create_schema(geo_signature=valid_sig)

        assert data.geo_signature == valid_sig

    def test_should_normalize_geo_signature_to_lowercase(self):
        uppercase_sig = "A" * 64
        data = build_queue_report_create_schema(geo_signature=uppercase_sig)

        assert data.geo_signature == "a" * 64

    def test_should_reject_when_geo_signature_is_missing(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_signature=None)

    def test_should_reject_geo_signature_shorter_than_64_chars(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_signature="a" * 63)

    def test_should_reject_geo_signature_longer_than_64_chars(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_signature="a" * 65)

    def test_should_reject_geo_signature_with_non_hex_characters(self):
        invalid_sig = "g" * 64
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_signature=invalid_sig)

    def test_should_reject_geo_signature_with_special_characters(self):
        invalid_sig = "!" * 64
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_signature=invalid_sig)

    def test_should_accept_geo_signature_with_all_hex_digits(self):
        # cobre todos os dígitos hex: 0-9 e a-f
        hex_sig = ("0123456789abcdef" * 4)[:64]
        data = build_queue_report_create_schema(geo_signature=hex_sig)

        assert data.geo_signature == hex_sig

    def test_should_accept_valid_geo_timestamp(self):
        ts = 1748166600
        data = build_queue_report_create_schema(geo_timestamp=ts)

        assert data.geo_timestamp == ts

    def test_should_reject_when_geo_timestamp_is_missing(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_timestamp=None)

    def test_should_reject_geo_timestamp_as_iso_string(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_timestamp="2026-05-25T10:30:00")

    def test_should_accept_geo_timestamp_in_the_past(self):
        ts = 1577836800  # 2020-01-01 00:00:00 UTC
        data = build_queue_report_create_schema(geo_timestamp=ts)

        assert data.geo_timestamp == ts

    def test_should_reject_negative_geo_timestamp(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_timestamp=-1)

    def test_should_reject_geo_timestamp_zero(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_timestamp=0)

    def test_should_accept_geo_timestamp_as_whole_number_float(self):
        # Pydantic v2 coerce float sem parte fracionária para int
        data = build_queue_report_create_schema(geo_timestamp=1748166600.0)

        assert data.geo_timestamp == 1748166600

    def test_should_reject_geo_timestamp_as_float_with_fraction(self):
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_timestamp=1748166600.5)

    def test_should_reject_geo_signature_with_whitespace(self):
        # Espaços não são caracteres hex
        with pytest.raises(ValidationError):
            build_queue_report_create_schema(geo_signature=" " * 64)

    def test_should_normalize_mixed_case_geo_signature(self):
        mixed_sig = "aAbBcCdDeEfF" * 5 + "aAbB"  # 60 + 4 = 64 chars
        data = build_queue_report_create_schema(geo_signature=mixed_sig)

        assert data.geo_signature == mixed_sig.lower()

    def test_should_include_geo_signature_in_model_dump(self):
        # geo_signature deve estar no dump para que o service possa excluí-lo via
        # _SCHEMA_ONLY_FIELDS ao construir o QueueReport
        data = build_queue_report_create_schema()

        assert "geo_signature" in data.model_dump()

    def test_should_include_geo_timestamp_in_model_dump(self):
        data = build_queue_report_create_schema()

        assert "geo_timestamp" in data.model_dump()

    def test_should_accept_large_accuracy_m(self):
        # Não há limite superior em accuracy_m
        data = build_queue_report_create_schema(accuracy_m="9999.99")

        assert data.accuracy_m == Decimal("9999.99")


class TestQueueReportResponseSchema:
    def test_should_validate_from_dict(self):
        payload = _build_report_response_payload()

        data = QueueReportResponse(**payload)

        assert data.public_id == payload["public_id"]
        assert data.status == ReportStatusEnum.SMALL
        assert data.meal_period == MealPeriodEnum.LUNCH

    def test_should_validate_from_orm_object(self):
        payload = _build_report_response_payload()
        orm_obj = SimpleNamespace(**payload)

        data = QueueReportResponse.model_validate(orm_obj)

        assert data.public_id == payload["public_id"]
        assert data.status == payload["status"]
        assert data.meal_period == payload["meal_period"]

    def test_should_not_expose_internal_id(self):
        payload = _build_report_response_payload()
        payload["id"] = 999

        data = QueueReportResponse(**payload)

        assert "id" not in data.model_dump()

    def test_should_not_expose_ru_id(self):
        payload = _build_report_response_payload()
        payload["ru_id"] = 1

        data = QueueReportResponse(**payload)

        assert "ru_id" not in data.model_dump()

    def test_should_not_expose_ip_hash(self):
        payload = _build_report_response_payload()
        payload["ip_hash"] = "a" * 64

        data = QueueReportResponse(**payload)

        assert "ip_hash" not in data.model_dump()

    def test_should_accept_all_valid_statuses(self):
        for status in ReportStatusEnum:
            payload = _build_report_response_payload(status=status)
            data = QueueReportResponse(**payload)
            assert data.status == status

    def test_should_accept_all_valid_meal_periods(self):
        for period in MealPeriodEnum:
            payload = _build_report_response_payload(meal_period=period)
            data = QueueReportResponse(**payload)
            assert data.meal_period == period

    def test_should_expose_all_expected_fields_in_dump(self):
        payload = _build_report_response_payload()

        data = QueueReportResponse(**payload)
        dump = data.model_dump()

        expected_fields = {
            "public_id",
            "status",
            "meal_period",
            "created_at",
        }
        assert set(dump.keys()) == expected_fields

    def test_should_not_expose_geo_signature(self):
        # geo_signature nunca é devolvido ao cliente
        payload = _build_report_response_payload()

        data = QueueReportResponse(**payload)

        assert "geo_signature" not in data.model_dump()

    def test_should_not_expose_geo_timestamp(self):
        payload = _build_report_response_payload()

        data = QueueReportResponse(**payload)

        assert "geo_timestamp" not in data.model_dump()

    def test_should_preserve_created_at_value(self):
        expected = datetime(2026, 5, 25, 10, 30, 0)
        payload = _build_report_response_payload(created_at=expected)

        data = QueueReportResponse(**payload)

        assert data.created_at == expected

    def test_should_require_meal_period(self):
        payload = _build_report_response_payload()
        del payload["meal_period"]

        with pytest.raises(ValidationError):
            QueueReportResponse(**payload)

    def test_should_require_created_at(self):
        payload = _build_report_response_payload()
        del payload["created_at"]

        with pytest.raises(ValidationError):
            QueueReportResponse(**payload)

    def test_should_require_public_id(self):
        payload = _build_report_response_payload()
        del payload["public_id"]

        with pytest.raises(ValidationError):
            QueueReportResponse(**payload)
