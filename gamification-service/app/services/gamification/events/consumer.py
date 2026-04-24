from __future__ import annotations

import asyncio
import json
import logging
import os
from uuid import UUID

import redis.asyncio as aioredis

from app.db.session import async_session_factory
from app.services.gamification.constants import ATTEND_MENTEE_SESSION, DELIVER_MENTOR_SESSION
from app.services.gamification.events.publisher import publish_credit_score_updated
from app.services.gamification.schemas.payloads import ProcessTransactionPayload
from app.services.gamification.services.exceptions import GamificationError, RuleInactiveError
from app.services.gamification.services.ledger_engine import process_transaction

log = logging.getLogger(__name__)

TOPIC_MENTORING_SESSIONS = "mentoring.sessions.events"

_task: asyncio.Task | None = None


async def _reward_user(uid_str: str, rule: str, idempotency_key: str) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            payload = ProcessTransactionPayload(
                user_id=UUID(str(uid_str)),
                rule_code=rule,
                amount=None,
                idempotency_key=idempotency_key,
            )
            try:
                out = await process_transaction(session, payload)
            except RuleInactiveError:
                # Rule disabled mid-flight: ignore event-driven transactions.
                return
            except GamificationError as exc:
                log.warning(
                    "session reward skipped user=%s rule=%s: %s",
                    uid_str,
                    rule,
                    exc,
                )
                return
            if not out.idempotent_replay:
                publish_credit_score_updated(
                    user_id=out.user_id,
                    balance=out.balance_after,
                    lifetime_earned=out.lifetime_earned,
                    transaction_id=str(out.transaction_id),
                )


async def _handle_session_completed(data: dict) -> None:
    if data.get("type") != "session_completed":
        return
    session_id = data.get("session_id")
    mentor_uid = data.get("mentor_user_id")
    mentee_uid = data.get("mentee_user_id")
    if not session_id or not mentor_uid or not mentee_uid:
        return
    sid = str(session_id)

    await _reward_user(str(mentor_uid), DELIVER_MENTOR_SESSION, f"session:{sid}:{DELIVER_MENTOR_SESSION}")
    await _reward_user(str(mentee_uid), ATTEND_MENTEE_SESSION, f"session:{sid}:{ATTEND_MENTEE_SESSION}")


async def _listen() -> None:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = aioredis.from_url(url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(TOPIC_MENTORING_SESSIONS)
    try:
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            try:
                data = json.loads(msg["data"])
            except json.JSONDecodeError:
                continue
            try:
                await _handle_session_completed(data)
            except Exception as exc:  # noqa: BLE001
                log.warning("gamification session event handler: %s", exc)
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
    _task = asyncio.create_task(_listen(), name="gamification-redis-listener")
    log.info("Gamification Redis listener started")


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
