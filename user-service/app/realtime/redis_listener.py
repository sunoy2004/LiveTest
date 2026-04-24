"""Async Redis subscriber → WebSocket push (same event loop as Uvicorn)."""

from __future__ import annotations

import asyncio
import json
import logging
import os

import redis.asyncio as aioredis

from app.services import event_bus
from app.services import ws_hub

log = logging.getLogger(__name__)

_task: asyncio.Task | None = None


async def _listen_loop() -> None:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = aioredis.from_url(url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(event_bus.EVENT_CHANNEL)
    log.info("redis subscriber listening on %s", event_bus.EVENT_CHANNEL)
    try:
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            try:
                data = json.loads(msg["data"])
            except json.JSONDecodeError:
                continue
            uids = data.get("notify_user_ids") or []
            await ws_hub.push_to_users(uids, data)
    except asyncio.CancelledError:
        raise
    finally:
        try:
            await pubsub.unsubscribe(event_bus.EVENT_CHANNEL)
            await pubsub.aclose()
            await client.aclose()
        except Exception:
            pass


async def start_listener() -> None:
    global _task
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_listen_loop(), name="redis-events")


async def stop_listener() -> None:
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
