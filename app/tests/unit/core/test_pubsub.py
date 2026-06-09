import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.pubsub import _run_listener, start_pubsub_listener


async def _async_messages(*messages):
    for msg in messages:
        yield msg


def _make_redis_with_pubsub(*messages):
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.aclose = AsyncMock()
    mock_pubsub.listen = MagicMock(return_value=_async_messages(*messages))

    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub

    return mock_redis, mock_pubsub


# ── TestRunListener ───────────────────────────────────────────────────────────


class TestRunListener:
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
            await _run_listener()

        mock_pubsub.subscribe.assert_called_once_with("snapshots")

    async def test_unsubscribes_and_closes_on_exit(self):
        mock_redis, mock_pubsub = _make_redis_with_pubsub()

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub.manager"),
        ):
            await _run_listener()

        mock_pubsub.unsubscribe.assert_called_once_with("snapshots")
        mock_pubsub.aclose.assert_called_once()

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
            await _run_listener()

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
            await _run_listener()

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
            await _run_listener()

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
            await _run_listener()

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
            await _run_listener()

        mock_manager.broadcast.assert_called_once_with(
            room="snapshots", payload=payload
        )

    async def test_cleanup_runs_even_when_broadcast_raises(self):
        payload = '{"type": "snapshot_updated"}'
        mock_redis, mock_pubsub = _make_redis_with_pubsub(
            {"type": "message", "data": payload},
        )
        mock_manager = AsyncMock()
        mock_manager.broadcast.side_effect = RuntimeError("broadcast failed")

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub.manager", mock_manager),
            pytest.raises(RuntimeError),
        ):
            await _run_listener()

        mock_pubsub.unsubscribe.assert_called_once_with("snapshots")
        mock_pubsub.aclose.assert_called_once()

    async def test_cleanup_exception_is_swallowed(self):
        # Cobre o `except Exception` do bloco finally: garante que erros
        # no unsubscribe/aclose não propagam e não quebram o fluxo.
        mock_redis, mock_pubsub = _make_redis_with_pubsub()
        mock_pubsub.unsubscribe.side_effect = RuntimeError("redis gone")

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub.manager"),
        ):
            # Não deve propagar — o except dentro do finally engole o erro
            await _run_listener()


# ── TestStartPubsubListener ───────────────────────────────────────────────────


class TestStartPubsubListener:
    async def test_cancelled_error_stops_loop_cleanly(self):
        # Cobre o `except asyncio.CancelledError` do while True:
        # simula shutdown da aplicação cancelando o listener após uma iteração.
        mock_redis, _ = _make_redis_with_pubsub()

        call_count = 0

        async def _run_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.CancelledError()

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub._run_listener", side_effect=_run_once),
            patch("app.core.pubsub.manager"),
            pytest.raises(asyncio.CancelledError),
        ):
            await start_pubsub_listener()

        assert call_count == 1

    async def test_reconnects_after_unexpected_exception(self):
        # Cobre o `except Exception` do while True:
        # simula uma queda do Redis seguida de reconexão bem-sucedida.
        mock_redis, _ = _make_redis_with_pubsub()

        call_count = 0

        async def _fail_then_cancel():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("redis unavailable")
            # Na segunda chamada simula CancelledError para sair do loop
            raise asyncio.CancelledError()

        with (
            patch(
                "app.core.pubsub.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch("app.core.pubsub._run_listener", side_effect=_fail_then_cancel),
            patch("app.core.pubsub.manager"),
            patch(
                "app.core.pubsub.asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep,
            pytest.raises(asyncio.CancelledError),
        ):
            await start_pubsub_listener()

        assert call_count == 2
        mock_sleep.assert_called_once_with(5)
