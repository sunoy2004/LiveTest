from __future__ import annotations

import asyncio
import logging

from app.ai.factory import get_embedding_provider
from app.infra.db import get_session_factory
from app.services import recommendation_cache
from app.services.graph import graph_store
from app.services.profile_ingestion import upsert_from_snapshot
from app.services.snapshot_client import fetch_matchmaking_snapshot

log = logging.getLogger(__name__)


def hydrate_graph_only() -> bool:
    snap = fetch_matchmaking_snapshot()
    if not snap:
        return False
    graph_store.hydrate_from_snapshot(snap)
    mentees = snap.get("mentees") or []
    return bool(mentees)


async def _bootstrap_pgvector(snap: dict) -> int:
    prov = get_embedding_provider()
    fac = get_session_factory()
    async with fac() as session:
        n = await upsert_from_snapshot(session, prov, snap)
        await session.commit()
    return n


async def bootstrap_from_user_service() -> bool:
    """
    Fetches matchmaking snapshot, hydrates the in-memory graph, and
    (when engine=pgvector) upserts match_profiles.
    Returns True when a snapshot was loaded successfully.
    """
    snap = fetch_matchmaking_snapshot()
    if not snap:
        return False
    graph_store.hydrate_from_snapshot(snap)
    from app.infra.settings import get_settings

    if get_settings().recommendation_engine == "pgvector":
        try:
            n = await _bootstrap_pgvector(snap)
            log.info("match_profiles upserted: %d", n)
        except Exception as e:  # noqa: BLE001
            log.warning("pgvector bootstrap failed: %s", e)
    return True


async def run_bootstrap_with_retry() -> None:
    for _ in range(60):
        if await bootstrap_from_user_service():
            return
        await asyncio.sleep(1)


async def rehydrate_from_user_service() -> bool:
    return await bootstrap_from_user_service()


async def run_full_reindex_from_user_service() -> dict:
    """
    Full sync from user-service snapshot: graph hydrate + pgvector upsert + cache flush.
    Returns a dict suitable for JSON (includes ok flag).
    """
    from app.infra.settings import get_settings

    snap = fetch_matchmaking_snapshot()
    if not snap:
        return {"ok": False, "detail": "snapshot_unavailable"}
    graph_store.hydrate_from_snapshot(snap)
    n_up = 0
    if get_settings().recommendation_engine == "pgvector":
        try:
            n_up = await _bootstrap_pgvector(snap)
            log.info("reindex: match_profiles upserted: %d", n_up)
        except Exception as e:  # noqa: BLE001
            log.exception("reindex: pgvector upsert failed")
            return {"ok": False, "detail": str(e)}
    n_cache = await recommendation_cache.invalidate_all_recommendation_caches()
    return {
        "ok": True,
        "mentor_rows_in_snapshot": len(snap.get("mentors") or []),
        "mentee_rows_in_snapshot": len(snap.get("mentees") or []),
        "match_profiles_upserted": n_up,
        "recommendation_cache_keys_deleted": n_cache,
    }
