from enum import StrEnum

from prometheus_client import Counter, Histogram


class QueueReportRejectReason(StrEnum):
    INVALID_GEO_SIGNATURE = "invalid_geo_signature"
    EXPIRED_GEO_SIGNATURE = "expired_geo_signature"
    COOLDOWN = "cooldown"
    OUTSIDE_GEOFENCE = "outside_geofence"
    OUTSIDE_MEAL_HOURS = "outside_meal_hours"
    MISSING_DEVICE_ID = "missing_device_id"
    OTHER = "other"


# Contadores
QUEUE_REPORTS_CREATED_TOTAL = Counter(
    "queue_reports_created_total",
    "Total de relatos enviados",
    [
        "restaurant_id",
        "restaurant_name",
        "report_status",
    ],
)
# report_status = QueueReport.status (ReportStatusEnum)

QUEUE_REPORTS_REJECTED_TOTAL = Counter(
    "queue_reports_rejected_total",
    "Relatos rejeitados",
    [
        "restaurant_id",
        "restaurant_name",
        "reason",
    ],
)
# reason = QueueReportRejectReason

QUEUE_REPORTS_CONFIDENCE_SCORE = Histogram(
    "queue_reports_confidence_score",
    "Confidence score dos relatos enviados",
    [
        "restaurant_id",
        "restaurant_name",
    ],
    buckets=(
        0.05,
        0.10,
        0.20,
        0.30,
        0.50,
        0.70,
        0.85,
        0.95,
        1.00,
    ),
)

QUEUE_REPORT_DISTANCE_METERS = Histogram(
    "queue_report_distance_meters",
    "Distância do usuário ao restaurante",
    [
        "restaurant_id",
        "restaurant_name",
        "geofence_result",  # "inside" ou "outside"
    ],
    buckets=(
        5,
        10,
        20,
        30,
        40,
        50,
        60,
        70,
        80,
        90,
        100,
        150,
        200,
    ),
)

RATE_LIMIT_BLOCKED_TOTAL = Counter(
    "rate_limit_blocked_total",
    "Total de bloqueios por rate limit",
    ["endpoint", "method", "limit"],
)
