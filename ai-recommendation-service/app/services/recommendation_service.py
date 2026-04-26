from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.settings import get_settings
from app.repositories.match_profiles import MatchProfileRepository
from app.services import recommendation_cache
from app.services.recommendation_enrichment import enrich_recommendation_rows
from app.services.snapshot_client import fetch_matchmaking_snapshot

log = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MatchProfileRepository(session)

    async def recommend(self, user_id: str, limit: int) -> list[dict[str, Any]]:
        s = get_settings()
        snap = fetch_matchmaking_snapshot()
        if s.recommendation_engine == "graph":
            from app.services.graph import graph_store

            rows = graph_store.recommend(user_id=user_id, limit=limit)
            return enrich_recommendation_rows(rows, snap)

        uid = uuid.UUID(user_id)
        key = recommendation_cache.cache_key(
            user_id, limit, hybrid=s.hybrid_scoring
        )
        try:
            cached = await recommendation_cache.get_cached(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            log.warning("Redis read failed (falling back to DB): %s", e)

        ok = await self._repo.source_row_exists_for_mentee(user_id=uid)
        if not ok:
            raise KeyError(user_id)

        rows = await self._repo.recommend(
            user_id=uid,
            limit=limit,
            hybrid=s.hybrid_scoring,
        )
        for r in rows:
            r["score"] = max(0.0, min(1.0, float(r.get("score", 0.0))))
        out = enrich_recommendation_rows([dict(r) for r in rows], snap)
        
        try:
            await recommendation_cache.set_cached(
                key,
                json.dumps(out),
                s.recommendation_cache_ttl,
            )
        except Exception as e:
            log.warning("Redis write failed: %s", e)

        return out
