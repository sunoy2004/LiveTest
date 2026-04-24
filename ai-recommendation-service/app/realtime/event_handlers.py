from __future__ import annotations

import logging
import uuid

from app.ai.factory import get_embedding_provider
from app.infra.db import get_session_factory
from app.infra.settings import get_settings
from app.repositories.match_interactions import MatchInteractionRepository
from app.services import recommendation_cache
from app.services.profile_ingestion import upsert_from_snapshot
from app.services.snapshot_client import fetch_matchmaking_snapshot

log = logging.getLogger(__name__)


async def on_session_completed(mentee_uid: str, mentor_uid: str) -> None:
    s = get_settings()
    if s.recommendation_engine != "pgvector":
        return
    try:
        fac = get_session_factory()
        async with fac() as session:
            await MatchInteractionRepository(session).insert_successful_mentorship(
                source_user_id=uuid.UUID(mentee_uid),
                target_user_id=uuid.UUID(mentor_uid),
            )
            await session.commit()
    except Exception as e:  # noqa: BLE001
        log.warning("pgvector session_completed interaction failed: %s", e)
        return
    try:
        await recommendation_cache.invalidate_user(mentee_uid)
        await recommendation_cache.invalidate_user(mentor_uid)
    except Exception as e:  # noqa: BLE001
        log.warning("cache invalidate failed: %s", e)


async def on_profile_updated(_user_id: str | None = None) -> None:
    if get_settings().recommendation_engine != "pgvector":
        return
    snap = fetch_matchmaking_snapshot()
    if not snap:
        return
    prov = get_embedding_provider()
    n = 0
    try:
        fac = get_session_factory()
        async with fac() as session:
            n = await upsert_from_snapshot(session, prov, snap)
            await session.commit()
    except Exception as e:  # noqa: BLE001
        log.warning("profile re-ingest failed: %s", e)
        return
    if _user_id:
        await recommendation_cache.invalidate_user(_user_id)
    log.info("re-ingested %d match_profiles from snapshot", n)
