from __future__ import annotations

import asyncio
import json
import logging
import os

import redis.asyncio as aioredis

from app.infra.settings import get_settings
from app.services import event_bus
from app.services.graph import graph_store

log = logging.getLogger(__name__)

_task: asyncio.Task | None = None


async def _listen() -> None:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = aioredis.from_url(url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(
        event_bus.TOPIC_MENTORING_CONNECTIONS,
        event_bus.TOPIC_MENTORING_SESSIONS,
        event_bus.TOPIC_MENTORING_PROFILES,
    )
    try:
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            try:
                data = json.loads(msg["data"])
            except json.JSONDecodeError:
                continue
            typ = data.get("type")
            eng = get_settings().recommendation_engine
            if typ == "mentorship_request_accepted":
                mentee_uid = data.get("mentee_user_id")
                mentor_uid = data.get("mentor_user_id")
                if mentee_uid and mentor_uid and eng == "graph":
                    graph_store.bump_edge(
                        mentee_user_id=str(mentee_uid),
                        mentor_user_id=str(mentor_uid),
                        delta=0.05,
                    )
            if typ == "session_completed":
                mentee_uid = data.get("mentee_user_id")
                mentor_uid = data.get("mentor_user_id")
                if mentee_uid and mentor_uid:
                    if eng == "graph":
                        graph_store.bump_edge(
                            mentee_user_id=str(mentee_uid),
                            mentor_user_id=str(mentor_uid),
                            delta=0.02,
                        )
                    else:
                        from app.realtime.event_handlers import on_session_completed

                        await on_session_completed(str(mentee_uid), str(mentor_uid))
            if typ == "profile_updated":
                from app.realtime.event_handlers import on_profile_updated

                await on_profile_updated(str(data.get("user_id") or ""))
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
    _task = asyncio.create_task(_listen(), name="ai-redis-listener")
    log.info("AI service Redis listener started")


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
