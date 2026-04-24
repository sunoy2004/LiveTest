from __future__ import annotations

import asyncio
import json
import logging
import os

import redis.asyncio as aioredis

from app.db.db import SessionLocal
from app.services import event_bus
from app.services.notify_service import record_notification

log = logging.getLogger(__name__)

_task: asyncio.Task | None = None


async def _listen() -> None:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = aioredis.from_url(url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(
        event_bus.TOPIC_MENTORING_CONNECTIONS,
        event_bus.TOPIC_MENTORING_SESSIONS,
        event_bus.TOPIC_ECONOMY_CREDITS,
    )
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
            if msg is None:
                continue
            if msg.get("type") != "message":
                continue
            topic = msg.get("channel") or "unknown"
            raw = msg.get("data")
            try:
                data = json.loads(raw) if isinstance(raw, (str, bytes, bytearray)) else raw
            except json.JSONDecodeError:
                continue
            event_type = str((data or {}).get("type") or "unknown")
            db = SessionLocal()
            try:
                record_notification(db, topic=str(topic), event_type=event_type, payload=data or {})
                db.commit()
            except Exception as exc:  # noqa: BLE001
                log.warning("notification persist failed: %s", exc)
                db.rollback()
            finally:
                db.close()
    except asyncio.CancelledError:
        raise
    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.aclose()
            await client.aclose()
        except Exception:
            pass


async def start_listener() -> None:
    global _task
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_listen(), name="notification-redis-listener")
    log.info("Notification service Redis listener started")


async def stop_listener() -> None:
    global _task
    if not _task:
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    _task = None