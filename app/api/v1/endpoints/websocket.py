from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.websocket_manager import manager

router = APIRouter(prefix="/ws", tags=["WebSocket Endpoints"])


@router.websocket("/snapshots")
async def snapshots_websocket(websocket: WebSocket):
    device_id: str | None = websocket.query_params.get("device_id")
    room = "snapshots"

    await manager.connect(websocket=websocket, room=room, device_id=device_id)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket=websocket, room=room, device_id=device_id)
