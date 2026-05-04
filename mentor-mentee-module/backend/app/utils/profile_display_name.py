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


def _short_join(items: list[str] | None, *, max_len: int) -> str:
    if not items:
        return ""
    s = ", ".join(str(x).strip() for x in items if x and str(x).strip())
    if not s:
        return ""
    return (s[: max_len - 1] + "…") if len(s) > max_len else s


def partner_display_name_from_mentor_profile(
    obj: object,
    *,
    user_id: uuid.UUID | None = None,
) -> str:
    """Session / roster partner line: real names only — never use bio as a person's name."""
    fn, ln = _strip_attr(obj, "first_name"), _strip_attr(obj, "last_name")
    composed = " ".join(p for p in (fn, ln) if p).strip()
    if composed:
        return composed
    full = _strip_attr(obj, "full_name")
    if full:
        return full
    for key in ("display_name", "headline", "public_name"):
        v = _strip_attr(obj, key)
        if v:
            return v[:120] + ("…" if len(v) > 120 else "")
    uid = user_id or getattr(obj, "user_id", None)
    return label_from_user_id(uid if isinstance(uid, uuid.UUID) else None)


def partner_display_name_from_mentee_profile(
    obj: object,
    *,
    user_id: uuid.UUID | None = None,
) -> str:
    """Partner line for mentee: names only — not learning-goals blobs."""
    fn, ln = _strip_attr(obj, "first_name"), _strip_attr(obj, "last_name")
    composed = " ".join(p for p in (fn, ln) if p).strip()
    if composed:
        return composed
    full = _strip_attr(obj, "full_name")
    if full:
        return full
    uid = user_id or getattr(obj, "user_id", None)
    return label_from_user_id(uid if isinstance(uid, uuid.UUID) else None)


def display_name_from_mentor_profile(
    obj: object,
    *,
    user_id: uuid.UUID | None = None,
) -> str:
    """Search / cards: names, then a short expertise hint — never a long bio paragraph."""
    base = partner_display_name_from_mentor_profile(obj, user_id=user_id)
    if base and not base.startswith("User "):
        return base
    exp = getattr(obj, "expertise", None) or getattr(obj, "expertise_areas", None) or []
    hint = _short_join(list(exp) if exp else [], max_len=72)
    if hint:
        return hint
    return base


def display_name_from_mentee_profile(
    obj: object,
    *,
    user_id: uuid.UUID | None = None,
) -> str:
    """Search / cards: names, then a very short goals hint before the anonymous label."""
    base = partner_display_name_from_mentee_profile(obj, user_id=user_id)
    if base and not base.startswith("User "):
        return base
    goals = getattr(obj, "learning_goals", None) or []
    hint = _short_join(list(goals) if goals else [], max_len=56)
    if hint:
        return hint
    return base


def mentor_card_public_display_name(
    obj: object,
    *,
    user_id: uuid.UUID | None = None,
) -> str:
    """Public mentor modal / AI merge: prefer person name; else compact expertise, not bio."""
    base = partner_display_name_from_mentor_profile(obj, user_id=user_id)
    if base and not base.startswith("User "):
        return base
    exp = getattr(obj, "expertise", None) or getattr(obj, "expertise_areas", None) or []
    hint = _short_join(list(exp) if exp else [], max_len=80)
    if hint:
        return hint
    return base


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
    return {r.user_id: partner_display_name_from_mentor_profile(r, user_id=r.user_id) for r in rows}


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
    return {r.user_id: partner_display_name_from_mentee_profile(r, user_id=r.user_id) for r in rows}
