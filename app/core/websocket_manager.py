from collections import defaultdict

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    def __init__(self):
        # room_id -> conjunto de WebSockets ativos
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)

        # device_id -> WebSocket ativo (1 conexão por dispositivo)
        self._device_connections: dict[str, WebSocket] = {}

        # WebSocket -> device_id (lookup reverso para limpeza em broadcast)
        self._ws_to_device: dict[WebSocket, str] = {}

    async def connect(
        self, websocket: WebSocket, room: str, device_id: str | None = None
    ) -> None:
        if device_id:
            old_ws = self._device_connections.get(device_id)

            if old_ws is not None and old_ws is not websocket:
                logger.info("Substituindo conexão anterior do device '%s'", device_id)

                try:
                    await old_ws.close(code=1000)
                except Exception:
                    pass

                self.rooms[room].discard(old_ws)
                self._ws_to_device.pop(old_ws, None)

        await websocket.accept()
        self.rooms[room].add(websocket)

        if device_id:
            self._device_connections[device_id] = websocket
            self._ws_to_device[websocket] = device_id

        logger.info(
            "Cliente conectado à sala '%s'. Total na sala: %d",
            room,
            len(self.rooms[room]),
        )

    def disconnect(
        self, websocket: WebSocket, room: str, device_id: str | None = None
    ) -> None:
        self.rooms[room].discard(websocket)

        resolved = device_id or self._ws_to_device.get(websocket)
        self._ws_to_device.pop(websocket, None)

        if resolved and self._device_connections.get(resolved) is websocket:
            del self._device_connections[resolved]

        logger.info(
            "Cliente desconectado da sala '%s'. Total na sala: %d",
            room,
            len(self.rooms[room]),
        )

    async def broadcast(self, room: str, payload: str) -> None:
        conexoes_mortas = []

        for websocket in self.rooms[room]:
            try:
                await websocket.send_text(payload)
            except Exception:
                conexoes_mortas.append(websocket)

        for websocket in conexoes_mortas:
            self.disconnect(websocket=websocket, room=room)


manager = WebSocketManager()
