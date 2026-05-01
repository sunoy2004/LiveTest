from __future__ import annotations
import uuid
from collections.abc import Sequence
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.protocol import EmbeddingProvider
from app.repositories.match_profiles import MatchProfileRepository

Role = str  # MENTOR | MENTEE | BOTH

def _join_tags(items: Sequence[str] | None) -> str:
    if not items:
        return ""
    return " ".join(x.strip() for x in items if isinstance(x, str) and x.strip())

def _build_combined_text(
    *,
    bio: str = "",
    skills: str = "",
    goals: str = "",
    education: str = "",
) -> str:
    parts = [
        bio or "",
        skills or "",
        goals or "",
        education or "",
    ]
    return " ".join(p.strip() for p in parts if p and p.strip()).strip() or " "

def _derive_role(mentor_uids: set[str], mentee_uids: set[str], uid: str) -> Role:
    m = uid in mentor_uids
    e = uid in mentee_uids
    if m and e:
        return "BOTH"
    if m:
        return "MENTOR"
    return "MENTEE"

async def upsert_from_snapshot(
    session: AsyncSession,
    provider: EmbeddingProvider,
    snapshot: dict[str, Any],
) -> int:
    """Rebuild match_profiles from mentoring-service snapshot. Returns row count written."""
    mentors = snapshot.get("mentors") or []
    mentees = snapshot.get("mentees") or []
    m_by: dict[str, dict] = {str(m["user_id"]): m for m in mentors if m.get("user_id")}
    me_by: dict[str, dict] = {str(m["user_id"]): m for m in mentees if m.get("user_id")}

    mentor_uids = set(m_by)
    mentee_uids = set(me_by)
    uids = mentor_uids | mentee_uids
    if not uids:
        return 0

    repo = MatchProfileRepository(session)
    n = 0
    for uid in uids:
        role = _derive_role(mentor_uids, mentee_uids, uid)
        mrow = m_by.get(uid, {})
        merow = me_by.get(uid, {})
        
        # Mapping new Mentoring Service schema to AI combined text
        is_active = True # Default to active
        
        if role == "MENTOR":
            text = _build_combined_text(
                bio=(mrow.get("bio") or ""),
                skills=_join_tags(mrow.get("expertise")),
            )
        elif role == "MENTEE":
            text = _build_combined_text(
                goals=_join_tags(merow.get("learning_goals")),
                education=(merow.get("education_level") or ""),
            )
        else: # BOTH
            text = _build_combined_text(
                bio=(mrow.get("bio") or ""),
                skills=_join_tags(mrow.get("expertise")),
                goals=_join_tags(merow.get("learning_goals")),
                education=(merow.get("education_level") or ""),
            )

        emb = await provider.generate_embedding(text)
        await repo.upsert(
            user_id=uuid.UUID(uid),
            role=role,
            is_active=is_active,
            combined_text_payload=text,
            embedding=emb,
        )
        n += 1
    return n
