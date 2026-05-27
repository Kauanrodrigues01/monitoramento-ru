from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.settings import settings


def utc_now() -> datetime:
    """Returns current time as timezone-aware UTC datetime."""
    return datetime.now(UTC)


def to_app_tz(dt: datetime) -> datetime:
    """Converts a UTC-aware datetime to the application's local timezone.

    Used when comparing against schedule times stored as local clock values
    (opens_at / closes_at), which always represent the physical restaurant hours.
    """
    return dt.astimezone(ZoneInfo(settings.APP_TIMEZONE))
