from __future__ import annotations

import json
import logging
import os
from typing import Any
from uuid import UUID

import redis

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TOPIC_ECONOMY_CREDITS = "economy.credits.events"


def _redis_sync() -> redis.Redis:
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def publish_credit_score_updated(
    *,
    user_id: UUID,
    balance: int,
    lifetime_earned: int | None = None,
    transaction_id: str | None = None,
) -> None:
    """Notify downstream services (same channel as legacy credit service)."""
    envelope: dict[str, Any] = {
        "type": "credit_score_updated",
        "user_id": str(user_id),
        "new_current_balance": balance,
        # legacy compatibility fields:
        "balance": balance,
        "xp": 0,
    }
    if lifetime_earned is not None:
        envelope["lifetime_earned"] = lifetime_earned
    if transaction_id:
        envelope["transaction_id"] = transaction_id
    try:
        _redis_sync().publish(TOPIC_ECONOMY_CREDITS, json.dumps(envelope, default=str))
    except Exception as exc:  # noqa: BLE001
        log.warning("publish CREDIT_SCORE_UPDATED failed: %s", exc)
