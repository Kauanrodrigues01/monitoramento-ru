from unittest.mock import AsyncMock, MagicMock, patch


from app.core.pubsub import start_pubsub_listener


async def _async_messages(*messages):
    for msg in messages:
        yield msg


def _make_redis_with_pubsub(*messages):
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.listen = MagicMock(return_value=_async_messages(*messages))

    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub

    return mock_redis, mock_pubsub


class TestStartPubsubListener:
    async def test_subscribes_to_snapshots_channel(self):
        mock_redis, mock_pubsub = _make_redis_with_pubsub()

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub.manager"),
        ):
            await start_pubsub_listener()

        mock_pubsub.subscribe.assert_called_once_with("snapshots")

    async def test_broadcasts_message_type_to_snapshots_room(self):
        payload = '{"type": "snapshot_updated"}'
        mock_redis, _ = _make_redis_with_pubsub(
            {"type": "message", "data": payload},
        )
        mock_manager = AsyncMock()

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub.manager", mock_manager),
        ):
            await start_pubsub_listener()

        mock_manager.broadcast.assert_called_once_with(
            room="snapshots", payload=payload
        )

    async def test_ignores_subscribe_confirmation_messages(self):
        mock_redis, _ = _make_redis_with_pubsub(
            {"type": "subscribe", "data": 1},
        )
        mock_manager = AsyncMock()

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub.manager", mock_manager),
        ):
            await start_pubsub_listener()

        mock_manager.broadcast.assert_not_called()

    async def test_ignores_psubscribe_messages(self):
        mock_redis, _ = _make_redis_with_pubsub(
            {"type": "psubscribe", "data": 1},
        )
        mock_manager = AsyncMock()

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub.manager", mock_manager),
        ):
            await start_pubsub_listener()

        mock_manager.broadcast.assert_not_called()

    async def test_broadcasts_each_message_independently(self):
        payload1 = '{"type": "snapshot_updated", "i": 1}'
        payload2 = '{"type": "snapshot_updated", "i": 2}'
        mock_redis, _ = _make_redis_with_pubsub(
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": payload1},
            {"type": "message", "data": payload2},
        )
        mock_manager = AsyncMock()

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub.manager", mock_manager),
        ):
            await start_pubsub_listener()

        assert mock_manager.broadcast.call_count == 2
        mock_manager.broadcast.assert_any_call(room="snapshots", payload=payload1)
        mock_manager.broadcast.assert_any_call(room="snapshots", payload=payload2)

    async def test_mixed_message_types_only_broadcasts_real_messages(self):
        payload = '{"type": "snapshot_updated"}'
        mock_redis, _ = _make_redis_with_pubsub(
            {"type": "subscribe", "data": 1},
            {"type": "psubscribe", "data": 1},
            {"type": "message", "data": payload},
            {"type": "unsubscribe", "data": 0},
        )
        mock_manager = AsyncMock()

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub.manager", mock_manager),
        ):
            await start_pubsub_listener()

        mock_manager.broadcast.assert_called_once_with(
            room="snapshots", payload=payload
        )
