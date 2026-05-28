from datetime import UTC, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from freezegun import freeze_time

from app.core.datetime_utils import to_app_tz, utc_now


class TestUtcNow:
    def test_returns_timezone_aware_datetime(self):
        result = utc_now()
        assert result.tzinfo is not None

    def test_returns_utc_timezone(self):
        result = utc_now()
        assert result.utcoffset().total_seconds() == 0

    @freeze_time("2026-05-27 15:30:00")
    def test_returns_frozen_utc_time(self):
        result = utc_now()
        assert result == datetime(2026, 5, 27, 15, 30, 0, tzinfo=UTC)

    def test_is_not_naive(self):
        result = utc_now()
        assert result != result.replace(tzinfo=None)


class TestToAppTz:
    def test_converts_utc_to_app_timezone(self):
        dt_utc = datetime(2026, 5, 27, 15, 0, 0, tzinfo=UTC)
        with patch("app.core.datetime_utils.settings") as mock_settings:
            mock_settings.APP_TIMEZONE = "America/Fortaleza"
            result = to_app_tz(dt_utc)
        assert result.tzinfo == ZoneInfo("America/Fortaleza")

    def test_adjusts_hour_by_utc_offset(self):
        # America/Fortaleza is UTC-3
        dt_utc = datetime(2026, 5, 27, 15, 0, 0, tzinfo=UTC)
        with patch("app.core.datetime_utils.settings") as mock_settings:
            mock_settings.APP_TIMEZONE = "America/Fortaleza"
            result = to_app_tz(dt_utc)
        assert result.hour == 12
        assert result.minute == 0

    def test_preserves_the_same_absolute_instant(self):
        dt_utc = datetime(2026, 5, 27, 15, 0, 0, tzinfo=UTC)
        with patch("app.core.datetime_utils.settings") as mock_settings:
            mock_settings.APP_TIMEZONE = "America/Fortaleza"
            result = to_app_tz(dt_utc)
        # Same point in time — offsets should cancel out
        assert result.astimezone(UTC) == dt_utc

    def test_result_is_timezone_aware(self):
        dt_utc = datetime(2026, 5, 27, 12, 0, 0, tzinfo=UTC)
        with patch("app.core.datetime_utils.settings") as mock_settings:
            mock_settings.APP_TIMEZONE = "America/Fortaleza"
            result = to_app_tz(dt_utc)
        assert result.tzinfo is not None

    def test_midnight_utc_is_previous_day_in_fortaleza(self):
        # 00:00 UTC = 21:00 previous day in UTC-3
        dt_utc = datetime(2026, 5, 27, 0, 0, 0, tzinfo=UTC)
        with patch("app.core.datetime_utils.settings") as mock_settings:
            mock_settings.APP_TIMEZONE = "America/Fortaleza"
            result = to_app_tz(dt_utc)
        assert result.day == 26
        assert result.hour == 21
