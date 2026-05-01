from __future__ import annotations
import asyncio
import logging
from sqlalchemy import text
from app.ai.factory import get_embedding_provider
from app.infra.db import get_session_factory
from app.services import recommendation_cache
from app.services.profile_ingestion import upsert_from_snapshot

log = logging.getLogger(__name__)

async def fetch_snapshot_from_local_db() -> dict:
    """
    Fetches the profile data directly from the mentoring service tables
    in the same database.
    """
    fac = get_session_factory()
    async with fac() as session:
        # Fetch mentors
        mentors_res = await session.execute(text(
            "SELECT user_id, bio, expertise, experience_years FROM mentor_profiles"
        ))
        mentors = [
            {"user_id": str(r[0]), "bio": r[1], "expertise": r[2], "experience_years": r[3]}
            for r in mentors_res.fetchall()
        ]

        # Fetch mentees
        mentees_res = await session.execute(text(
            "SELECT user_id, learning_goals, education_level FROM mentee_profiles"
        ))
        mentees = [
            {"user_id": str(r[0]), "learning_goals": r[1], "education_level": r[2]}
            for r in mentees_res.fetchall()
        ]

        # Fetch connections
        conns_res = await session.execute(text(
            "SELECT mentor_user_id, mentee_user_id FROM mentorship_connections WHERE status = 'ACTIVE'"
        ))
        connections = [
            {"mentor_id": str(r[0]), "mentee_id": str(r[1])}
            for r in conns_res.fetchall()
        ]

        return {
            "mentors": mentors,
            "mentees": mentees,
            "connections": connections
        }

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
    
    n_cache = await recommendation_cache.invalidate_all_recommendation_caches()
    return {
        "ok": True,
        "mentor_rows": len(snap["mentors"]),
        "mentee_rows": len(snap["mentees"]),
        "match_profiles_upserted": n_up,
        "recommendation_cache_keys_deleted": n_cache,
    }
