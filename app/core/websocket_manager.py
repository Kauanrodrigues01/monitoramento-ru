from collections import defaultdict

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    def __init__(self):
        # room_id -> conjunto de WebSockets ativos
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, room: str) -> None:
        await websocket.accept()
        self.rooms[room].add(websocket)
        logger.info("Cliente conectado à sala '%s'. Total na sala: %d", room, len(self.rooms[room]))

    def disconnect(self, websocket: WebSocket, room: str) -> None:
        self.rooms[room].discard(websocket)
        logger.info("Cliente desconectado da sala '%s'. Total na sala: %d", room, len(self.rooms[room]))

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
