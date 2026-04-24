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
    headline: str = "",
    title: str = "",
    company: str = "",
    experiences: str = "",
) -> str:
    parts = [
        headline or "",
        title or "",
        company or "",
        bio or "",
        experiences or "",
        skills or "",
        goals or "",
        education or "",
    ]
    return " ".join(p.strip() for p in parts if p and p.strip()).strip() or " "


def _derive_role(mentor_ids: set[str], mentee_ids: set[str], uid: str) -> Role:
    m = uid in mentor_ids
    e = uid in mentee_ids
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
    """Rebuild match_profiles from user-service snapshot. Returns row count written."""
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
        is_accepting = bool(mrow.get("is_accepting_requests", True))
        exp_text = ""
        exps = mrow.get("professional_experiences") or []
        if isinstance(exps, list):
            chunks: list[str] = []
            for e in exps:
                if not isinstance(e, dict):
                    continue
                t = (e.get("title") or "").strip()
                c = (e.get("company") or "").strip()
                s = (e.get("summary") or "").strip()
                chunk = " ".join(x for x in [t, c, s] if x)
                if chunk:
                    chunks.append(chunk)
            exp_text = " ".join(chunks)
        if role == "MENTOR":
            is_active = is_accepting
            text = _build_combined_text(
                headline=(mrow.get("headline") or "") or "",
                title=(mrow.get("current_title") or "") or "",
                company=(mrow.get("current_company") or "") or "",
                bio=(mrow.get("bio") or "") or "",
                experiences=exp_text,
                skills=_join_tags(mrow.get("expertise_areas")),
                goals="",
                education="",
            )
        elif role == "MENTEE":
            is_active = True
            text = _build_combined_text(
                bio="",
                skills="",
                goals=_join_tags(merow.get("learning_goals")),
                education=(merow.get("education_level") or "") or "",
            )
        else:
            is_active = is_accepting
            text = _build_combined_text(
                headline=(mrow.get("headline") or "") or "",
                title=(mrow.get("current_title") or "") or "",
                company=(mrow.get("current_company") or "") or "",
                bio=(mrow.get("bio") or "") or "",
                experiences=exp_text,
                skills=_join_tags(mrow.get("expertise_areas")),
                goals=_join_tags(merow.get("learning_goals")),
                education=(merow.get("education_level") or "") or "",
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
