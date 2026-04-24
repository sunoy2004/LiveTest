from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis

from app.infra.settings import Settings, get_settings

log = logging.getLogger(__name__)

_client: Any = None


def _get_redis(*, url: str | None = None):
    global _client
    if _client is None:
        s = get_settings() if not url else None
        u = url or (s and s.redis_url) or "redis://localhost:6379/0"
        _client = aioredis.from_url(u, decode_responses=True)
    return _client


async def get_cached(
    key: str, *, url: str | None = None
) -> str | None:
    r = _get_redis(url=url)
    return await r.get(key)


async def set_cached(
    key: str,
    value: str,
    ttl: int,
    *,
    url: str | None = None,
) -> None:
    r = _get_redis(url=url)
    await r.setex(key, ttl, value)


def cache_key(
    user_id: str,
    limit: int,
    *,
    settings: Settings | None = None,
    hybrid: bool = False,
) -> str:
    s = settings or get_settings()
    h = 1 if hybrid else 0
    return f"rec:{s.rec_cache_key_version}:{s.recommendation_engine}:h{h}:{user_id}:{limit}"


async def invalidate_all_recommendation_caches() -> int:
    """Delete all keys used for GET /recommendations caching (prefix rec:)."""
    r = _get_redis()
    n = 0
    try:
        async for k in r.scan_iter(match="rec:*", count=200):
            if isinstance(k, bytes):
                k = k.decode()
            await r.delete(k)
            n += 1
    except Exception as e:  # noqa: BLE001
        log.warning("cache invalidate-all failed: %s", e)
    log.info("invalidated %d recommendation cache keys (full flush)", n)
    return n


async def invalidate_user(user_id: str) -> None:
    r = _get_redis()
    pattern = f"rec:*:{user_id}:*"
    n = 0
    try:
        async for k in r.scan_iter(match=pattern, count=100):
            if isinstance(k, bytes):
                k = k.decode()
            await r.delete(k)
            n += 1
    except Exception as e:  # noqa: BLE001
        log.warning("cache invalidate failed: %s", e)
    log.debug("invalidated %d cache keys for user %s", n, user_id)
