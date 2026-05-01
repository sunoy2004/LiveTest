"""Resolve default mentee session booking cost from gamification BOOK_MENTOR_SESSION rule."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BOOK_MENTOR_SESSION_RULE_CODE = "BOOK_MENTOR_SESSION"
_CACHE_OK_TTL_SEC = 120.0
_CACHE_ERR_TTL_SEC = 30.0

_cache_expiry: float = 0.0
_cache_value: int | None = None


async def resolve_default_book_session_credits(fallback: int) -> int:
    """
    Return `base_credit_value` for BOOK_MENTOR_SESSION from gamification when configured.

    If `GAMIFICATION_SERVICE_URL` / `INTERNAL_API_TOKEN` are unset, or the request fails,
    returns `fallback` (typically `mentor_tiers.PEER.session_credit_cost`).
    """
    global _cache_expiry, _cache_value

    fb = max(int(fallback), 0)
    settings = get_settings()
    base = (settings.gamification_service_url or "").strip().rstrip("/")
    token = (settings.internal_api_token or "").strip()
    if not base or not token:
        _cache_value = None
        _cache_expiry = 0.0
        return fb

    now = time.monotonic()
    if _cache_value is not None and now < _cache_expiry:
        return _cache_value

    url = f"{base}/internal/activity-rules/{BOOK_MENTOR_SESSION_RULE_CODE}"
    resolved = fb
    ttl = _CACHE_ERR_TTL_SEC
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url, headers={"X-Internal-Token": token})
        if resp.status_code == 200:
            data: dict[str, Any] = resp.json()
            raw = data.get("base_credit_value")
            if isinstance(raw, bool):
                pass
            elif isinstance(raw, int):
                if raw > 0:
                    resolved = raw
                ttl = _CACHE_OK_TTL_SEC
            elif isinstance(raw, float):
                try:
                    v = int(raw)
                    if v > 0:
                        resolved = v
                        ttl = _CACHE_OK_TTL_SEC
                except (ValueError, OverflowError):
                    pass
            elif isinstance(raw, str):
                try:
                    v = int(raw.strip())
                    if v > 0:
                        resolved = v
                        ttl = _CACHE_OK_TTL_SEC
                except ValueError:
                    pass
        else:
            logger.warning(
                "gamification BOOK_MENTOR_SESSION rule fetch HTTP %s: %s",
                resp.status_code,
                (resp.text or "")[:200],
            )
    except Exception as exc:
        logger.warning("gamification BOOK_MENTOR_SESSION fetch failed: %s", exc)

    resolved = max(int(resolved), 0)
    _cache_value = resolved
    _cache_expiry = now + ttl
    return resolved
