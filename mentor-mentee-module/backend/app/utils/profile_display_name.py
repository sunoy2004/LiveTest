"""Readable labels from mentor/mentee profile rows (no `users.email` on replicas)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MenteeProfile, MentorProfile
from app.utils.display_name import label_from_user_id


def _strip_attr(obj: object, attr: str) -> str:
    v = getattr(obj, attr, None)
    if v is None:
        return ""
    return str(v).strip()


def display_name_from_mentor_profile(
    obj: object,
    *,
    user_id: uuid.UUID | None = None,
) -> str:
    fn, ln = _strip_attr(obj, "first_name"), _strip_attr(obj, "last_name")
    composed = " ".join(p for p in (fn, ln) if p).strip()
    if composed:
        return composed
    full = _strip_attr(obj, "full_name")
    if full:
        return full
    bio = _strip_attr(obj, "bio")
    if bio:
        return (bio[:97] + "…") if len(bio) > 100 else bio
    exp = getattr(obj, "expertise", None) or getattr(obj, "expertise_areas", None) or []
    if exp:
        s = ", ".join(str(x).strip() for x in exp if x and str(x).strip())
        if s:
            return (s[:77] + "…") if len(s) > 80 else s
    uid = user_id or getattr(obj, "user_id", None)
    return label_from_user_id(uid if isinstance(uid, uuid.UUID) else None)


def display_name_from_mentee_profile(
    obj: object,
    *,
    user_id: uuid.UUID | None = None,
) -> str:
    fn, ln = _strip_attr(obj, "first_name"), _strip_attr(obj, "last_name")
    composed = " ".join(p for p in (fn, ln) if p).strip()
    if composed:
        return composed
    full = _strip_attr(obj, "full_name")
    if full:
        return full
    goals = getattr(obj, "learning_goals", None) or []
    if goals:
        s = ", ".join(str(x).strip() for x in goals if x and str(x).strip())
        if s:
            return (s[:97] + "…") if len(s) > 100 else s
    edu = _strip_attr(obj, "education_level")
    if edu:
        return edu
    uid = user_id or getattr(obj, "user_id", None)
    return label_from_user_id(uid if isinstance(uid, uuid.UUID) else None)


def search_name_fields_from_mentor(obj: object) -> dict[str, str | None]:
    """Shape `SearchResult` name fields for the mentoring SPA (first/last vs full_name)."""
    fn, ln = _strip_attr(obj, "first_name"), _strip_attr(obj, "last_name")
    if fn or ln:
        return {"first_name": fn or None, "last_name": ln or None, "full_name": None}
    full = _strip_attr(obj, "full_name")
    if full:
        return {"first_name": None, "last_name": None, "full_name": full}
    return {
        "first_name": None,
        "last_name": None,
        "full_name": display_name_from_mentor_profile(obj, user_id=getattr(obj, "user_id", None)),
    }


def search_name_fields_from_mentee(obj: object) -> dict[str, str | None]:
    fn, ln = _strip_attr(obj, "first_name"), _strip_attr(obj, "last_name")
    if fn or ln:
        return {"first_name": fn or None, "last_name": ln or None, "full_name": None}
    full = _strip_attr(obj, "full_name")
    if full:
        return {"first_name": None, "last_name": None, "full_name": full}
    return {
        "first_name": None,
        "last_name": None,
        "full_name": display_name_from_mentee_profile(obj, user_id=getattr(obj, "user_id", None)),
    }


async def mentor_display_name_map(
    session: AsyncSession,
    user_ids: Iterable[uuid.UUID],
) -> dict[uuid.UUID, str]:
    ids = {u for u in user_ids if u is not None}
    if not ids:
        return {}
    rows = (
        await session.execute(select(MentorProfile).where(MentorProfile.user_id.in_(ids)))
    ).scalars().all()
    return {r.user_id: display_name_from_mentor_profile(r, user_id=r.user_id) for r in rows}


async def mentee_display_name_map(
    session: AsyncSession,
    user_ids: Iterable[uuid.UUID],
) -> dict[uuid.UUID, str]:
    ids = {u for u in user_ids if u is not None}
    if not ids:
        return {}
    rows = (
        await session.execute(select(MenteeProfile).where(MenteeProfile.user_id.in_(ids)))
    ).scalars().all()
    return {r.user_id: display_name_from_mentee_profile(r, user_id=r.user_id) for r in rows}
