import pytest
from pydantic import ValidationError

from app.schemas.metrics_schemas import MetricsSummaryResponse


def _build_payload(**kwargs) -> dict:
    data = {
        "total_active_restaurants": 3,
        "open_now": 2,
        "reports_last_15m": 10,
        "reports_today": 42,
        "status_distribution": {"NO_DATA": 1, "SMALL": 2},
        "avg_confidence": 0.85,
    }
    data.update(kwargs)
    return data


class TestMetricsSummaryResponseSchema:
    def test_should_create_with_valid_data(self):
        data = MetricsSummaryResponse(**_build_payload())

        assert data.total_active_restaurants == 3
        assert data.open_now == 2
        assert data.reports_last_15m == 10
        assert data.reports_today == 42
        assert data.status_distribution == {"NO_DATA": 1, "SMALL": 2}
        assert data.avg_confidence == 0.85

    def test_should_accept_avg_confidence_as_none(self):
        data = MetricsSummaryResponse(**_build_payload(avg_confidence=None))

        assert data.avg_confidence is None

    def test_should_accept_empty_status_distribution(self):
        data = MetricsSummaryResponse(**_build_payload(status_distribution={}))

        assert data.status_distribution == {}

    def test_should_accept_zero_counts(self):
        data = MetricsSummaryResponse(
            **_build_payload(
                total_active_restaurants=0,
                open_now=0,
                reports_last_15m=0,
                reports_today=0,
            )
        )

        assert data.total_active_restaurants == 0
        assert data.open_now == 0
        assert data.reports_last_15m == 0
        assert data.reports_today == 0

    def test_should_reject_when_total_active_restaurants_is_missing(self):
        payload = _build_payload()
        del payload["total_active_restaurants"]

        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**payload)

    def test_should_reject_when_open_now_is_missing(self):
        payload = _build_payload()
        del payload["open_now"]

        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**payload)

    def test_should_reject_when_reports_last_15m_is_missing(self):
        payload = _build_payload()
        del payload["reports_last_15m"]

        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**payload)

    def test_should_reject_when_reports_today_is_missing(self):
        payload = _build_payload()
        del payload["reports_today"]

        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**payload)

    def test_should_reject_when_status_distribution_is_missing(self):
        payload = _build_payload()
        del payload["status_distribution"]

        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**payload)

    def test_should_reject_when_avg_confidence_field_is_absent(self):
        payload = _build_payload()
        del payload["avg_confidence"]

        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**payload)

    def test_should_expose_all_expected_fields_in_dump(self):
        data = MetricsSummaryResponse(**_build_payload())

        expected_fields = {
            "total_active_restaurants",
            "open_now",
            "reports_last_15m",
            "reports_today",
            "status_distribution",
            "avg_confidence",
        }
        assert set(data.model_dump().keys()) == expected_fields

    def test_should_preserve_status_distribution_keys(self):
        distribution = {"NO_QUEUE": 1, "SMALL": 3, "MEDIUM": 2, "LARGE": 0}
        data = MetricsSummaryResponse(
            **_build_payload(status_distribution=distribution)
        )

        assert data.status_distribution == distribution

    def test_should_preserve_avg_confidence_float_precision(self):
        data = MetricsSummaryResponse(**_build_payload(avg_confidence=0.73))

        assert data.avg_confidence == 0.73

    def test_should_reject_invalid_type_for_total_active_restaurants(self):
        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**_build_payload(total_active_restaurants="abc"))

    def test_should_reject_invalid_type_for_open_now(self):
        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**_build_payload(open_now="abc"))

    def test_should_reject_invalid_type_for_reports_last_15m(self):
        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**_build_payload(reports_last_15m="abc"))

    def test_should_reject_invalid_type_for_reports_today(self):
        with pytest.raises(ValidationError):
            MetricsSummaryResponse(**_build_payload(reports_today="abc"))
