"""On-demand match_profiles row when mentee_profiles exists but bootstrap missed the user."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embedding_provider
from app.repositories.match_profiles import MatchProfileRepository
from app.services.profile_ingestion import upsert_from_snapshot

log = logging.getLogger(__name__)


async def ensure_mentee_embedding(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """
    If `mentee_profiles` has this user but `match_profiles` has no MENTEE/BOTH row,
    build one embedding row (same pipeline as full snapshot ingest).
    """
    repo = MatchProfileRepository(session)
    if await repo.source_row_exists_for_mentee(user_id=user_id):
        return True

    try:
        res = await session.execute(
            text(
                """
                SELECT user_id::text, learning_goals, COALESCE(education_level, '')
                FROM mentee_profiles
                WHERE user_id = :uid
                """
            ),
            {"uid": user_id},
        )
        row = res.first()
    except Exception as exc:
        log.warning("ensure_mentee_embedding: mentee_profiles query failed: %s", exc)
        return False

    if row is None:
        return False

    uid_s, goals, edu = row
    snap = {
        "mentors": [],
        "mentees": [
            {
                "user_id": uid_s,
                "learning_goals": list(goals) if goals is not None else [],
                "education_level": edu or "",
            }
        ],
        "connections": [],
    }
    try:
        prov = get_embedding_provider()
        n = await upsert_from_snapshot(session, prov, snap)
        if n > 0:
            log.info(
                "ensure_mentee_embedding: upserted match_profiles for mentee %s",
                uid_s,
            )
        return n > 0
    except Exception as exc:
        log.warning("ensure_mentee_embedding: upsert failed: %s", exc)
        return False
