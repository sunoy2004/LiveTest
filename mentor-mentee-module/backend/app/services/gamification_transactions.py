"""Call gamification-service internal APIs (ledger) from mentoring."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.services.book_mentor_session_credits import BOOK_MENTOR_SESSION_RULE_CODE

logger = logging.getLogger(__name__)


async def fetch_wallet_balance_from_gamification(user_id: uuid.UUID) -> int | None:
    """
    GET {GAMIFICATION}/internal/wallet/{user_id} with X-Internal-Token.
    Returns current_balance, or None if misconfigured / unreachable / error.
    """
    settings = get_settings()
    base = (settings.gamification_service_url or "").strip().rstrip("/")
    token = (settings.internal_api_token or "").strip()
    if not base or not token:
        return None
    url = f"{base}/internal/wallet/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"X-Internal-Token": token})
    except httpx.RequestError as exc:
        logger.warning("gamification wallet fetch failed: %s", exc)
        return None
    if resp.status_code != status.HTTP_200_OK:
        logger.warning(
            "gamification wallet HTTP %s: %s",
            resp.status_code,
            (resp.text or "")[:200],
        )
        return None
    try:
        data = resp.json()
        raw = data.get("current_balance")
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int):
            return max(0, raw)
        if isinstance(raw, float):
            return max(0, int(raw))
    except Exception as exc:
        logger.warning("gamification wallet parse failed: %s", exc)
    return None


async def deduct_book_mentor_session_credits(
    *,
    mentee_user_id: uuid.UUID,
    amount: int,
    idempotency_key: str,
) -> int:
    """
    POST /internal/transactions/deduct. Returns wallet balance_after on success.

    Forwards 402 when the mentee has insufficient credits; 503 when gamification is
    misconfigured or unreachable.
    """
    if amount < 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Session booking credit amount must be at least 1",
        )

    settings = get_settings()
    base = (settings.gamification_service_url or "").strip().rstrip("/")
    token = (settings.internal_api_token or "").strip()
    if not base or not token:
        logger.error("GAMIFICATION_SERVICE_URL or INTERNAL_API_TOKEN is not set")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gamification service is not configured",
        )

    url = f"{base}/internal/transactions/deduct"
    body: dict[str, Any] = {
        "user_id": str(mentee_user_id),
        "rule_code": BOOK_MENTOR_SESSION_RULE_CODE,
        "amount": int(amount),
        "idempotency_key": idempotency_key,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                headers={"X-Internal-Token": token, "Content-Type": "application/json"},
                json=body,
            )
    except httpx.RequestError as exc:
        logger.warning("gamification deduct request failed: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reach gamification service",
        ) from exc

    if resp.status_code == status.HTTP_200_OK:
        data = resp.json()
        raw = data.get("balance_after")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            return int(raw)
        logger.warning("gamification deduct missing balance_after: %s", data)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from gamification service",
        )

    if resp.status_code == status.HTTP_402_PAYMENT_REQUIRED:
        detail = "Insufficient credits"
        try:
            j = resp.json()
            if isinstance(j, dict) and j.get("detail"):
                detail = str(j["detail"])
        except Exception:
            pass
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, detail=detail)

    if resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Booking rule cooldown active; try again shortly",
        )

    logger.warning(
        "gamification deduct HTTP %s: %s",
        resp.status_code,
        (resp.text or "")[:300],
    )
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Gamification service could not process the deduction",
    )
