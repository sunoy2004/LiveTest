"""
Redis Pub/Sub envelope for event-driven notifications.
Sync publish (safe from SQLAlchemy request threads); async consumer in realtime listener.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from typing import Any
from uuid import UUID

import redis

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
EVENT_CHANNEL = "app:events"

TOPIC_SESSION_SCHEDULED = "session_scheduled"
TOPIC_SESSION_COMPLETED = "session_completed"
TOPIC_CREDIT_UPDATED = "credit_updated"
TOPIC_MENTORSHIP_REQUESTED = "mentorship_requested"
TOPIC_MENTORSHIP_ACCEPTED = "mentorship_request_accepted"
TOPIC_SESSION_BOOKING_REQUESTED = "session_booking_requested"
TOPIC_SESSION_BOOKING_REJECTED = "session_booking_rejected"

# Cross-service event topics (simulated Pub/Sub)
TOPIC_MENTORING_SESSIONS = "mentoring.sessions.events"
TOPIC_MENTORING_CONNECTIONS = "mentoring.connections.events"
TOPIC_MENTORING_PROFILES = "mentoring.profiles.matching"
TOPIC_ECONOMY_CREDITS = "economy.credits.events"


def subscribe_event(topic: str, handler: Callable[[dict[str, Any]], None]) -> None:
    """
    Extension hook for in-process subscribers. The live path is Redis
    (`EVENT_CHANNEL`) → `app.realtime.redis_listener` → WebSocket clients.
    """
    _ = (topic, handler)


def _redis_sync() -> redis.Redis:
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def publish_event(
    topic: str,
    payload: dict[str, Any],
    *,
    notify_user_ids: list[UUID],
    fanout_economy_redis: bool = True,
) -> None:
    """Fire-and-forget publish; failures are logged (degraded mode without Redis)."""
    envelope = {
        "topic": topic,
        "payload": payload,
        "notify_user_ids": [str(u) for u in notify_user_ids],
    }
    try:
        r = _redis_sync()
        # 1) UI realtime channel (WS fan-out)
        r.publish(EVENT_CHANNEL, json.dumps(envelope, default=str))

        # 2) Microservice event topics (event-driven architecture)
        if topic in (TOPIC_SESSION_SCHEDULED, TOPIC_SESSION_COMPLETED):
            r.publish(
                TOPIC_MENTORING_SESSIONS,
                json.dumps(
                    {
                        "type": topic,
                        **payload,
                        "notify_user_ids": [str(u) for u in notify_user_ids],
                    },
                    default=str,
                ),
            )
        elif topic == TOPIC_CREDIT_UPDATED and fanout_economy_redis:
            r.publish(
                TOPIC_ECONOMY_CREDITS,
                json.dumps(
                    {
                        "type": topic,
                        **payload,
                        "notify_user_ids": [str(u) for u in notify_user_ids],
                    },
                    default=str,
                ),
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("redis publish failed: %s", exc)


def publish_profile_matching_event(payload: dict[str, Any]) -> None:
    """Notify AI / matchmaking that user profile data changed (Redis Pub/Sub)."""
    try:
        r = _redis_sync()
        r.publish(
            TOPIC_MENTORING_PROFILES,
            json.dumps(
                {
                    "type": "profile_updated",
                    **payload,
                },
                default=str,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("redis publish (profile matching) failed: %s", exc)


def publish_connections_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    notify_user_ids: list[UUID],
) -> None:
    """Publish to WebSocket channel and mentoring.connections.events."""
    envelope = {
        "topic": event_type,
        "payload": payload,
        "notify_user_ids": [str(u) for u in notify_user_ids],
    }
    try:
        r = _redis_sync()
        r.publish(EVENT_CHANNEL, json.dumps(envelope, default=str))
        r.publish(
            TOPIC_MENTORING_CONNECTIONS,
            json.dumps(
                {
                    "type": event_type,
                    **payload,
                    "notify_user_ids": [str(u) for u in notify_user_ids],
                },
                default=str,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("redis publish failed: %s", exc)
