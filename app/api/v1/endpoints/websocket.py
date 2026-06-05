from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from app.core.rate_limiter import limiter
from app.core.rate_limits import WS_CONNECT_RATE_LIMIT
from app.core.websocket_manager import manager

router = APIRouter(prefix="/ws", tags=["WebSocket Endpoints"])


@router.websocket("/snapshots")
@limiter.limit(WS_CONNECT_RATE_LIMIT)
async def snapshots_websocket(websocket: WebSocket, request: Request):
    device_id: str | None = websocket.query_params.get("device_id")
    room = "snapshots"

    await manager.connect(websocket=websocket, room=room, device_id=device_id)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket=websocket, room=room, device_id=device_id)
