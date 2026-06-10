from decimal import Decimal
from typing import Literal

from app.core.observability.business_metrics import (
    QUEUE_REPORT_DISTANCE_METERS,
    QUEUE_REPORTS_CONFIDENCE_SCORE,
    QUEUE_REPORTS_CREATED_TOTAL,
    QUEUE_REPORTS_REJECTED_TOTAL,
    RATE_LIMIT_BLOCKED_TOTAL,
    QueueReportRejectReason,
)
from app.models.restaurant import Restaurant


def track_queue_report_created(
    *,
    restaurant: Restaurant,
    report_status: str,
) -> None:
    QUEUE_REPORTS_CREATED_TOTAL.labels(
        restaurant_id=str(restaurant.id),
        restaurant_name=restaurant.name,
        report_status=report_status,
    ).inc()


def track_queue_report_rejected(
    *,
    restaurant: Restaurant,
    reason: QueueReportRejectReason,
) -> None:
    QUEUE_REPORTS_REJECTED_TOTAL.labels(
        restaurant_id=str(restaurant.id),
        restaurant_name=restaurant.name,
        reason=reason.value,
    ).inc()


def observe_queue_report_confidence_score(
    *,
    restaurant: Restaurant,
    confidence_score: float | Decimal,
) -> None:
    QUEUE_REPORTS_CONFIDENCE_SCORE.labels(
        restaurant_id=str(restaurant.id),
        restaurant_name=restaurant.name,
    ).observe(float(confidence_score))


def observe_queue_report_distance(
    *,
    restaurant: Restaurant,
    distance_meters: float | Decimal,
    geofence_result: Literal["inside", "outside"],
) -> None:
    QUEUE_REPORT_DISTANCE_METERS.labels(
        restaurant_id=str(restaurant.id),
        restaurant_name=restaurant.name,
        geofence_result=geofence_result,
    ).observe(float(distance_meters))


def track_rate_limit_blocked(
    *,
    endpoint: str,
    method: str,
    limit: str,
) -> None:
    RATE_LIMIT_BLOCKED_TOTAL.labels(
        endpoint=endpoint,
        method=method,
        limit=limit,
    ).inc()
