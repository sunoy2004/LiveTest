from __future__ import annotations

import logging
import os
import time
from typing import Any
from uuid import UUID

import httpx

log = logging.getLogger(__name__)

GAMIFICATION_SERVICE_URL = os.getenv("GAMIFICATION_SERVICE_URL", "").rstrip("/")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")

RULE_BOOK_MENTOR_SESSION = "BOOK_MENTOR_SESSION"
DEFAULT_BOOK_MENTOR_SESSION_CREDITS = 10
_RULE_BASE_CACHE: dict[str, tuple[float, int]] = {}
_RULE_CACHE_TTL_SEC = 45.0

RULE_RESOLVE_NO_SHOW_REFUND = "RESOLVE_NO_SHOW_REFUND"
RULE_MENTOR_NO_SHOW_PENALTY = "MENTOR_NO_SHOW_PENALTY"


def get_balance(user_id: UUID) -> dict[str, Any] | None:
    if not GAMIFICATION_SERVICE_URL:
        return None
    try:
        r = httpx.get(
            f"{GAMIFICATION_SERVICE_URL}/balance/{user_id}",
            timeout=10.0,
        )
        if r.status_code != 200:
            log.warning("gamification balance HTTP %s", r.status_code)
            return None
        return r.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("gamification balance failed: %s", exc)
        return None


def deduct(user_id: UUID, amount: int) -> tuple[bool, int | None]:
    """
    Returns (ok, new_balance_if_ok).
    When GAMIFICATION_SERVICE_URL is unset, returns (False, None) so caller can fall back or fail.
    """
    if not GAMIFICATION_SERVICE_URL:
        return False, None
    try:
        r = httpx.post(
            f"{GAMIFICATION_SERVICE_URL}/deduct",
            json={"user_id": str(user_id), "amount": amount},
            timeout=15.0,
        )
        data = r.json() if r.content else {}
        if r.status_code != 200:
            log.warning("gamification deduct HTTP %s %s", r.status_code, data)
            return False, None
        ok = bool(data.get("ok"))
        bal = data.get("balance")
        return ok, int(bal) if bal is not None else None
    except Exception as exc:  # noqa: BLE001
        log.warning("gamification deduct failed: %s", exc)
        return False, None


def deduct_booking(
    *,
    user_id: UUID,
    amount: int,
    idempotency_key: str,
    rule_code: str = "BOOK_MENTOR_SESSION",
) -> tuple[bool, int | None]:
    """
    Preferred path: internal deduct API (idempotent, rule-driven).
    Returns (ok, new_balance_if_ok). On insufficient funds returns (False, None).
    """
    if not GAMIFICATION_SERVICE_URL or not INTERNAL_API_TOKEN:
        return False, None
    try:
        r = httpx.post(
            f"{GAMIFICATION_SERVICE_URL}/internal/transactions/deduct",
            headers={"X-Internal-Token": INTERNAL_API_TOKEN},
            json={
                "user_id": str(user_id),
                "rule_code": rule_code,
                "amount": amount,
                "idempotency_key": idempotency_key,
            },
            timeout=20.0,
        )
        if r.status_code == 402:
            return False, None
        if r.status_code != 200:
            log.warning("gamification internal deduct HTTP %s %s", r.status_code, r.text[:200])
            return False, None
        data = r.json() if r.content else {}
        bal = data.get("balance_after")
        return True, int(bal) if bal is not None else None
    except Exception as exc:  # noqa: BLE001
        log.warning("gamification internal deduct failed: %s", exc)
        return False, None


def earn_internal(
    *,
    user_id: UUID,
    rule_code: str,
    idempotency_key: str,
    amount: int | None = None,
) -> tuple[bool, int | None]:
    """
    Idempotent earn via gamification internal API (ledger + rules).
    When amount is None, gamification uses the rule's base_credit_value.
    Returns (ok, balance_after_if_ok).
    """
    if not GAMIFICATION_SERVICE_URL or not INTERNAL_API_TOKEN:
        return False, None
    if amount is not None and amount < 1:
        return False, None
    try:
        payload: dict[str, object] = {
            "user_id": str(user_id),
            "rule_code": rule_code,
            "idempotency_key": idempotency_key,
        }
        if amount is not None:
            payload["amount"] = amount
        r = httpx.post(
            f"{GAMIFICATION_SERVICE_URL}/internal/transactions/earn",
            headers={"X-Internal-Token": INTERNAL_API_TOKEN},
            json=payload,
            timeout=20.0,
        )
        if r.status_code != 200:
            log.warning(
                "gamification internal earn HTTP %s %s",
                r.status_code,
                r.text[:200],
            )
            return False, None
        data = r.json() if r.content else {}
        bal = data.get("balance_after")
        return True, int(bal) if bal is not None else None
    except Exception as exc:  # noqa: BLE001
        log.warning("gamification internal earn failed: %s", exc)
        return False, None


def fetch_activity_rule_base_credit(rule_code: str) -> int | None:
    """
    Read activity_rules.base_credit_value from gamification (internal API).
    Returns None if service unreachable or rule missing.
    """
    if not GAMIFICATION_SERVICE_URL or not INTERNAL_API_TOKEN:
        return None
    try:
        r = httpx.get(
            f"{GAMIFICATION_SERVICE_URL}/internal/activity-rules/{rule_code}",
            headers={"X-Internal-Token": INTERNAL_API_TOKEN},
            timeout=10.0,
        )
        if r.status_code != 200:
            log.warning(
                "gamification activity rule %s HTTP %s",
                rule_code,
                r.status_code,
            )
            return None
        data = r.json() if r.content else {}
        v = data.get("base_credit_value")
        if v is None:
            return None
        return max(0, int(v))
    except Exception as exc:  # noqa: BLE001
        log.warning("gamification activity rule fetch failed: %s", exc)
        return None


def get_book_mentor_session_base_credits() -> int:
    """
    Default session booking price for mentors without base_credit_override.
    Uses gamification BOOK_MENTOR_SESSION.base_credit_value; falls back to DEFAULT_* if unavailable.
    Cached briefly to avoid hammering gamification on mentor lists.
    """
    now = time.monotonic()
    cached = _RULE_BASE_CACHE.get(RULE_BOOK_MENTOR_SESSION)
    if cached is not None and now - cached[0] < _RULE_CACHE_TTL_SEC:
        return cached[1]

    raw = fetch_activity_rule_base_credit(RULE_BOOK_MENTOR_SESSION)
    val = raw if raw is not None and raw > 0 else DEFAULT_BOOK_MENTOR_SESSION_CREDITS
    _RULE_BASE_CACHE[RULE_BOOK_MENTOR_SESSION] = (now, val)
    return val


def add_credits(user_id: UUID, amount: int) -> bool:
    if not GAMIFICATION_SERVICE_URL or amount <= 0:
        return True
    try:
        r = httpx.post(
            f"{GAMIFICATION_SERVICE_URL}/add",
            json={"user_id": str(user_id), "amount": amount, "xp": 0},
            timeout=15.0,
        )
        return r.status_code == 200
    except Exception as exc:  # noqa: BLE001
        log.warning("gamification add failed: %s", exc)
        return False
