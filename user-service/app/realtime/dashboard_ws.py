from __future__ import annotations

from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, Query

from app import auth
from app.services import ws_hub


async def handle_dashboard_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT from User Service"),
) -> None:
    await websocket.accept()
    try:
        payload = auth.verify_token(token)
        uid = str(UUID(payload["user_id"]))
    except Exception:
        await websocket.close(code=4401)
        return

    await ws_hub.register(uid, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_hub.unregister(uid, websocket)
