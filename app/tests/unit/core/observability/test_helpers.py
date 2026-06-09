from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.core.observability.business_metrics import QueueReportRejectReason
from app.core.observability.helpers import (
    observe_queue_report_confidence_score,
    observe_queue_report_distance,
    track_business_request,
    track_queue_report_created,
    track_queue_report_rejected,
    track_rate_limit_blocked,
)

_PATCH_CREATED = "app.core.observability.helpers.QUEUE_REPORTS_CREATED_TOTAL"
_PATCH_REJECTED = "app.core.observability.helpers.QUEUE_REPORTS_REJECTED_TOTAL"
_PATCH_CONFIDENCE = "app.core.observability.helpers.QUEUE_REPORTS_CONFIDENCE_SCORE"
_PATCH_DISTANCE = "app.core.observability.helpers.QUEUE_REPORT_DISTANCE_METERS"
_PATCH_RATE_LIMIT = "app.core.observability.helpers.RATE_LIMIT_BLOCKED_TOTAL"
_PATCH_BUSINESS = "app.core.observability.helpers.BUSINESS_REQUESTS_TOTAL"


def _make_metric_mock():
    """Returns a mock that supports .labels(...).inc() and .labels(...).observe()."""
    labeled = MagicMock()
    metric = MagicMock()
    metric.labels.return_value = labeled
    return metric, labeled


def _make_restaurant(id_=1, name="RU Central"):
    restaurant = MagicMock()
    restaurant.id = id_
    restaurant.name = name
    return restaurant


# ── TestTrackQueueReportCreated ───────────────────────────────────────────────


class TestTrackQueueReportCreated:
    def test_calls_labels_with_correct_arguments(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant(id_=1, name="RU Central")

        with patch(_PATCH_CREATED, metric):
            track_queue_report_created(restaurant=restaurant, report_status="long")

        metric.labels.assert_called_once_with(
            restaurant_id="1",
            restaurant_name="RU Central",
            report_status="long",
        )

    def test_calls_inc(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant()

        with patch(_PATCH_CREATED, metric):
            track_queue_report_created(restaurant=restaurant, report_status="short")

        labeled.inc.assert_called_once()

    def test_restaurant_id_is_stringified(self):
        metric, _ = _make_metric_mock()
        restaurant = _make_restaurant(id_=99)

        with patch(_PATCH_CREATED, metric):
            track_queue_report_created(restaurant=restaurant, report_status="short")

        call_kwargs = metric.labels.call_args.kwargs
        assert call_kwargs["restaurant_id"] == "99"
        assert isinstance(call_kwargs["restaurant_id"], str)


# ── TestTrackQueueReportRejected ──────────────────────────────────────────────


class TestTrackQueueReportRejected:
    def test_calls_labels_with_correct_arguments(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant(id_=2, name="RU Fortaleza")

        with patch(_PATCH_REJECTED, metric):
            track_queue_report_rejected(
                restaurant=restaurant,
                reason=QueueReportRejectReason.COOLDOWN,
            )

        metric.labels.assert_called_once_with(
            restaurant_id="2",
            restaurant_name="RU Fortaleza",
            reason=QueueReportRejectReason.COOLDOWN.value,
        )

    def test_calls_inc(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant()

        with patch(_PATCH_REJECTED, metric):
            track_queue_report_rejected(
                restaurant=restaurant,
                reason=QueueReportRejectReason.OUTSIDE_GEOFENCE,
            )

        labeled.inc.assert_called_once()

    def test_reason_value_is_used_not_enum_itself(self):
        metric, _ = _make_metric_mock()
        restaurant = _make_restaurant()

        with patch(_PATCH_REJECTED, metric):
            track_queue_report_rejected(
                restaurant=restaurant,
                reason=QueueReportRejectReason.MISSING_DEVICE_ID,
            )

        call_kwargs = metric.labels.call_args.kwargs
        assert call_kwargs["reason"] == QueueReportRejectReason.MISSING_DEVICE_ID.value
        assert isinstance(call_kwargs["reason"], str)


# ── TestObserveQueueReportConfidenceScore ─────────────────────────────────────


class TestObserveQueueReportConfidenceScore:
    def test_calls_labels_with_correct_arguments(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant(id_=3, name="RU Redenção")

        with patch(_PATCH_CONFIDENCE, metric):
            observe_queue_report_confidence_score(
                restaurant=restaurant,
                confidence_score=0.95,
            )

        metric.labels.assert_called_once_with(
            restaurant_id="3",
            restaurant_name="RU Redenção",
        )

    def test_calls_observe_with_float_value(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant()

        with patch(_PATCH_CONFIDENCE, metric):
            observe_queue_report_confidence_score(
                restaurant=restaurant,
                confidence_score=0.75,
            )

        labeled.observe.assert_called_once_with(0.75)

    def test_decimal_is_converted_to_float(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant()

        with patch(_PATCH_CONFIDENCE, metric):
            observe_queue_report_confidence_score(
                restaurant=restaurant,
                confidence_score=Decimal("0.85"),
            )

        observed_value = labeled.observe.call_args.args[0]
        assert isinstance(observed_value, float)
        assert observed_value == pytest.approx(0.85)


# ── TestObserveQueueReportDistance ────────────────────────────────────────────


class TestObserveQueueReportDistance:
    def test_calls_labels_with_correct_arguments_inside(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant(id_=4, name="RU Sul")

        with patch(_PATCH_DISTANCE, metric):
            observe_queue_report_distance(
                restaurant=restaurant,
                distance_meters=120.5,
                geofence_result="inside",
            )

        metric.labels.assert_called_once_with(
            restaurant_id="4",
            restaurant_name="RU Sul",
            geofence_result="inside",
        )

    def test_calls_labels_with_correct_arguments_outside(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant()

        with patch(_PATCH_DISTANCE, metric):
            observe_queue_report_distance(
                restaurant=restaurant,
                distance_meters=500.0,
                geofence_result="outside",
            )

        call_kwargs = metric.labels.call_args.kwargs
        assert call_kwargs["geofence_result"] == "outside"

    def test_calls_observe_with_float_value(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant()

        with patch(_PATCH_DISTANCE, metric):
            observe_queue_report_distance(
                restaurant=restaurant,
                distance_meters=200.0,
                geofence_result="inside",
            )

        labeled.observe.assert_called_once_with(200.0)

    def test_decimal_distance_is_converted_to_float(self):
        metric, labeled = _make_metric_mock()
        restaurant = _make_restaurant()

        with patch(_PATCH_DISTANCE, metric):
            observe_queue_report_distance(
                restaurant=restaurant,
                distance_meters=Decimal("150.25"),
                geofence_result="inside",
            )

        observed_value = labeled.observe.call_args.args[0]
        assert isinstance(observed_value, float)
        assert observed_value == pytest.approx(150.25)


# ── TestTrackRateLimitBlocked ─────────────────────────────────────────────────


class TestTrackRateLimitBlocked:
    def test_calls_labels_with_correct_arguments(self):
        metric, labeled = _make_metric_mock()

        with patch(_PATCH_RATE_LIMIT, metric):
            track_rate_limit_blocked(
                endpoint="/api/v1/queue-reports",
                method="POST",
                limit="10/minute",
            )

        metric.labels.assert_called_once_with(
            endpoint="/api/v1/queue-reports",
            method="POST",
            limit="10/minute",
        )

    def test_calls_inc(self):
        metric, labeled = _make_metric_mock()

        with patch(_PATCH_RATE_LIMIT, metric):
            track_rate_limit_blocked(
                endpoint="/api/v1/queue-reports",
                method="POST",
                limit="10/minute",
            )

        labeled.inc.assert_called_once()


# ── TestTrackBusinessRequest ──────────────────────────────────────────────────


class TestTrackBusinessRequest:
    def test_calls_labels_with_correct_arguments(self):
        metric, labeled = _make_metric_mock()

        with patch(_PATCH_BUSINESS, metric):
            track_business_request(
                endpoint="/api/v1/restaurants",
                method="GET",
                status_code=200,
            )

        metric.labels.assert_called_once_with(
            endpoint="/api/v1/restaurants",
            method="GET",
            status_code="200",
        )

    def test_status_code_is_stringified(self):
        metric, _ = _make_metric_mock()

        with patch(_PATCH_BUSINESS, metric):
            track_business_request(
                endpoint="/api/v1/restaurants",
                method="POST",
                status_code=201,
            )

        call_kwargs = metric.labels.call_args.kwargs
        assert call_kwargs["status_code"] == "201"
        assert isinstance(call_kwargs["status_code"], str)

    def test_calls_inc(self):
        metric, labeled = _make_metric_mock()

        with patch(_PATCH_BUSINESS, metric):
            track_business_request(
                endpoint="/api/v1/restaurants",
                method="GET",
                status_code=404,
            )

        labeled.inc.assert_called_once()
