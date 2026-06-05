import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from app.models.queue_snapshot import SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.services.websocket_service import SnapshotWebSocketService

_NOW = datetime(2026, 5, 27, 12, 0, 0, tzinfo=UTC)
_RESTAURANT_PUBLIC_ID = uuid4()


def _make_snapshot(
    meal_period: MealPeriodEnum = MealPeriodEnum.LUNCH,
    current_status: SnapshotStatusEnum = SnapshotStatusEnum.SMALL,
    reports_last_15m: int = 3,
    last_report_at: datetime | None = None,
    confidence_score: Decimal = Decimal("0.85"),
) -> SimpleNamespace:
    return SimpleNamespace(
        meal_period=meal_period,
        current_status=current_status,
        reports_last_15m=reports_last_15m,
        last_report_at=last_report_at,
        confidence_score=confidence_score,
    )


class TestPublishSnapshot:
    async def test_publishes_to_snapshots_channel(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot()

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        channel = mock_redis.publish.call_args[0][0]
        assert channel == "snapshots"

    async def test_payload_contains_correct_type(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot()

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["type"] == "snapshot_updated"

    async def test_payload_contains_restaurant_public_id(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot()

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["restaurant_public_id"] == str(_RESTAURANT_PUBLIC_ID)

    async def test_payload_contains_current_status(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot(current_status=SnapshotStatusEnum.LARGE)

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["current_status"] == "LARGE"

    async def test_payload_contains_meal_period(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot(meal_period=MealPeriodEnum.DINNER)

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["meal_period"] == "DINNER"

    async def test_payload_contains_reports_last_15m(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot(reports_last_15m=7)

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["reports_last_15m"] == 7

    async def test_payload_contains_confidence_score_as_float(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot(confidence_score=Decimal("0.75"))

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["confidence_score"] == 0.75

    async def test_data_freshness_minutes_is_none_when_no_last_report(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot(last_report_at=None)

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["data_freshness_minutes"] is None

    async def test_data_freshness_minutes_calculated_from_last_report_at(self):
        mock_redis = AsyncMock()
        last_report_at = _NOW - timedelta(minutes=10)
        snapshot = _make_snapshot(last_report_at=last_report_at)

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["data_freshness_minutes"] == 10

    async def test_data_freshness_minutes_clamped_to_zero_on_clock_skew(self):
        mock_redis = AsyncMock()
        # last_report_at no futuro (clock skew)
        last_report_at = _NOW + timedelta(minutes=5)
        snapshot = _make_snapshot(last_report_at=last_report_at)

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["data_freshness_minutes"] == 0

    async def test_updated_at_uses_utc_now(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot()

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["updated_at"].startswith(_NOW.strftime("%Y-%m-%dT%H:%M:%S"))

    async def test_publish_called_exactly_once(self):
        mock_redis = AsyncMock()
        snapshot = _make_snapshot()

        with (
            patch("app.services.websocket_service.get_redis", new_callable=AsyncMock, return_value=mock_redis),
            patch("app.services.websocket_service.utc_now", return_value=_NOW),
        ):
            await SnapshotWebSocketService.publish_snapshot(snapshot, _RESTAURANT_PUBLIC_ID)

        mock_redis.publish.assert_called_once()
