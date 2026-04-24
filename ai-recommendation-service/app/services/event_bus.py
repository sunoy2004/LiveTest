from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

TOPIC_MENTORING_SESSIONS = "mentoring.sessions.events"
TOPIC_MENTORING_CONNECTIONS = "mentoring.connections.events"
TOPIC_MENTORING_PROFILES = "mentoring.profiles.matching"
TOPIC_ECONOMY_CREDITS = "economy.credits.events"


def redis_sync() -> redis.Redis:
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def publish(topic: str, event: dict[str, Any]) -> None:
    try:
        redis_sync().publish(topic, json.dumps(event, default=str))
    except Exception as exc:  # noqa: BLE001
        log.warning("publish failed topic=%s err=%s", topic, exc)