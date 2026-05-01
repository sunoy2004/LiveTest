from __future__ import annotations
import asyncio
import logging

from app.ai.factory import get_embedding_provider
from app.infra.db import get_session_factory
from app.infra.settings import get_settings
from app.services import recommendation_cache
from app.services.mentoring_snapshot import build_mentoring_snapshot
from app.services.profile_ingestion import upsert_from_snapshot

log = logging.getLogger(__name__)


async def fetch_snapshot_from_local_db() -> dict:
    """Load mentor/mentee/connection rows from mentoring domain tables (same DB as match_profiles)."""
    fac = get_session_factory()
    async with fac() as session:
        return await build_mentoring_snapshot(session)

async def bootstrap_from_local_db() -> bool:
    """
    Directly builds embeddings from local database tables.
    """
    try:
        snap = await fetch_snapshot_from_local_db()
        if not snap["mentors"] and not snap["mentees"]:
            log.warning("No profiles found in local database for bootstrapping")
            return False

        prov = get_embedding_provider()
        fac = get_session_factory()
        async with fac() as session:
            n = await upsert_from_snapshot(session, prov, snap)
            await session.commit()
            log.info("Local bootstrap: match_profiles upserted: %d", n)

        if get_settings().recommendation_engine == "graph":
            from app.services.graph import graph_store

            graph_store.hydrate_from_snapshot(snap)

        await recommendation_cache.invalidate_all_recommendation_caches()
        return True
    except Exception as e:
        log.error("Bootstrap from local DB failed: %s", e)
        return False

async def run_bootstrap_with_retry() -> None:
    for _ in range(60):
        if await bootstrap_from_local_db():
            return
        await asyncio.sleep(2)

async def run_full_reindex_from_local_db() -> dict:
    snap = await fetch_snapshot_from_local_db()
    prov = get_embedding_provider()
    fac = get_session_factory()
    async with fac() as session:
        n_up = await upsert_from_snapshot(session, prov, snap)
        await session.commit()

    if get_settings().recommendation_engine == "graph":
        from app.services.graph import graph_store

        graph_store.hydrate_from_snapshot(snap)

    n_cache = await recommendation_cache.invalidate_all_recommendation_caches()
    return {
        "ok": True,
        "mentor_rows": len(snap["mentors"]),
        "mentee_rows": len(snap["mentees"]),
        "match_profiles_upserted": n_up,
        "recommendation_cache_keys_deleted": n_cache,
    }


async def rehydrate_from_user_service() -> bool:
    """
    Rebuild `match_profiles` from the mentoring database. Used when a mentee has no embedding row yet.
    """
    return await bootstrap_from_local_db()
