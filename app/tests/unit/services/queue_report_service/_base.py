import hashlib
from decimal import Decimal

from app.models.queue_reports import QueueReport, ReportStatusEnum
from app.models.restaurant import MealPeriodEnum

# ── constants ───────────────────────────────────────────────────────────────────
_IP = "192.168.1.1"
_IP_HASH = hashlib.sha256(_IP.encode()).hexdigest()
_UNKNOWN_IP_HASH = hashlib.sha256("unknown".encode()).hexdigest()
_DEVICE_ID = "test-device-abc123"
_DEVICE_HASH = hashlib.sha256(_DEVICE_ID.encode()).hexdigest()
_GEO_TIMESTAMP = 1748166600

_PATCH_GEO_SIG = "app.services.queue_report_service.GeoSignatureService.validate"
_PATCH_HAVERSINE = "app.services.queue_report_service.GeoUtils.haversine_distance_m"
_PATCH_CONFIDENCE = "app.services.queue_report_service.ConfidenceScoreService.calculate_confidence_score"
_PATCH_SETTINGS = "app.services.queue_report_service.settings"


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_queue_report(**kwargs) -> QueueReport:
    defaults = dict(
        ru_id=1,
        meal_period=MealPeriodEnum.LUNCH,
        ip_hash=_IP_HASH,
        device_hash=_DEVICE_HASH,
        confidence_score=Decimal("1.00"),
        status=ReportStatusEnum.SMALL,
        lat=Decimal("-3.747361"),
        lng=Decimal("-38.523060"),
    )
    defaults.update(kwargs)
    return QueueReport(**defaults)


def _setup_full_happy_path(
    mock_repo,
    mock_restaurant_repo,
    mock_meal_period_service,
    restaurant,
    meal_period=MealPeriodEnum.LUNCH,
    mock_snapshot_repo=None,
) -> QueueReport:
    """Configures all mocks for the happy path. Returns the mocked QueueReport."""
    queue_report = _make_queue_report(ru_id=restaurant.id, meal_period=meal_period)
    mock_restaurant_repo.get_by_public_id.return_value = restaurant
    mock_meal_period_service.resolve.return_value = meal_period
    mock_repo.get_last_by_device_hash_within_minutes.return_value = None
    mock_repo.create.return_value = queue_report
    if mock_snapshot_repo is not None:
        mock_snapshot_repo.get_by_ru_id_and_meal_period.return_value = None
    return queue_report
