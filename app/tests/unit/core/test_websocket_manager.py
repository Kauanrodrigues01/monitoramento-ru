from unittest.mock import AsyncMock

import pytest

from app.core.websocket_manager import WebSocketManager


def _make_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


class TestConnect:
    async def test_calls_accept_on_websocket(self):
        manager = WebSocketManager()
        ws = _make_ws()

        await manager.connect(ws, "snapshots")

        ws.accept.assert_called_once()

    async def test_adds_websocket_to_room(self):
        manager = WebSocketManager()
        ws = _make_ws()

        await manager.connect(ws, "snapshots")

        assert ws in manager.rooms["snapshots"]

    async def test_multiple_clients_in_same_room(self):
        manager = WebSocketManager()
        ws1, ws2 = _make_ws(), _make_ws()

        await manager.connect(ws1, "snapshots")
        await manager.connect(ws2, "snapshots")

        assert len(manager.rooms["snapshots"]) == 2

    async def test_clients_in_different_rooms_are_isolated(self):
        manager = WebSocketManager()
        ws1, ws2 = _make_ws(), _make_ws()

        await manager.connect(ws1, "snapshots")
        await manager.connect(ws2, "other")

        assert ws1 not in manager.rooms["other"]
        assert ws2 not in manager.rooms["snapshots"]


class TestDisconnect:
    async def test_removes_websocket_from_room(self):
        manager = WebSocketManager()
        ws = _make_ws()
        await manager.connect(ws, "snapshots")

        manager.disconnect(ws, "snapshots")

        assert ws not in manager.rooms["snapshots"]

    async def test_does_not_raise_when_websocket_not_in_room(self):
        manager = WebSocketManager()
        ws = _make_ws()

        manager.disconnect(ws, "snapshots")  # não deve levantar exceção

    async def test_other_clients_remain_after_one_disconnects(self):
        manager = WebSocketManager()
        ws1, ws2 = _make_ws(), _make_ws()
        await manager.connect(ws1, "snapshots")
        await manager.connect(ws2, "snapshots")

        manager.disconnect(ws1, "snapshots")

        assert ws1 not in manager.rooms["snapshots"]
        assert ws2 in manager.rooms["snapshots"]


class TestBroadcast:
    async def test_sends_payload_to_all_clients_in_room(self):
        manager = WebSocketManager()
        ws1, ws2 = _make_ws(), _make_ws()
        await manager.connect(ws1, "snapshots")
        await manager.connect(ws2, "snapshots")

        await manager.broadcast("snapshots", "payload")

        ws1.send_text.assert_called_once_with("payload")
        ws2.send_text.assert_called_once_with("payload")

    async def test_does_not_send_to_clients_in_other_rooms(self):
        manager = WebSocketManager()
        ws_target, ws_other = _make_ws(), _make_ws()
        await manager.connect(ws_target, "snapshots")
        await manager.connect(ws_other, "other")

        await manager.broadcast("snapshots", "payload")

        ws_target.send_text.assert_called_once()
        ws_other.send_text.assert_not_called()

    async def test_empty_room_broadcast_does_not_raise(self):
        manager = WebSocketManager()

        await manager.broadcast("snapshots", "payload")  # não deve levantar exceção

    async def test_dead_connection_is_removed_after_broadcast(self):
        manager = WebSocketManager()
        ws = _make_ws()
        ws.send_text.side_effect = Exception("conexão perdida")
        await manager.connect(ws, "snapshots")

        await manager.broadcast("snapshots", "payload")

        assert ws not in manager.rooms["snapshots"]

    async def test_healthy_connection_kept_when_sibling_dies(self):
        manager = WebSocketManager()
        ws_dead, ws_alive = _make_ws(), _make_ws()
        ws_dead.send_text.side_effect = Exception("conexão perdida")
        await manager.connect(ws_dead, "snapshots")
        await manager.connect(ws_alive, "snapshots")

        await manager.broadcast("snapshots", "payload")

        assert ws_dead not in manager.rooms["snapshots"]
        assert ws_alive in manager.rooms["snapshots"]

    async def test_broadcasts_correct_payload_string(self):
        manager = WebSocketManager()
        ws = _make_ws()
        await manager.connect(ws, "snapshots")

        payload = '{"type": "snapshot_updated", "status": "SMALL"}'
        await manager.broadcast("snapshots", payload)

        ws.send_text.assert_called_once_with(payload)
