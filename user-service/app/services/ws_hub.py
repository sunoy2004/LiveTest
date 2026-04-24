"""In-process WebSocket fan-out keyed by user id (string)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket

_lock = asyncio.Lock()
_by_user: dict[str, list[WebSocket]] = {}


async def register(user_id: str, websocket: WebSocket) -> None:
    async with _lock:
        _by_user.setdefault(user_id, []).append(websocket)


async def unregister(user_id: str, websocket: WebSocket) -> None:
    async with _lock:
        lst = _by_user.get(user_id)
        if not lst:
            return
        if websocket in lst:
            lst.remove(websocket)
        if not lst:
            del _by_user[user_id]


async def push_to_users(user_ids: list[str], message: dict[str, Any]) -> None:
    raw = json.dumps(message, default=str)
    async with _lock:
        sockets: list[tuple[str, WebSocket]] = []
        for uid in user_ids:
            for ws in list(_by_user.get(uid, [])):
                sockets.append((uid, ws))
    for uid, ws in sockets:
        try:
            await ws.send_text(raw)
        except Exception:
            await unregister(uid, ws)
