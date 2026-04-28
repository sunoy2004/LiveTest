from __future__ import annotations

import uuid
from typing import Any


def _norm_uid(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    try:
        return str(uuid.UUID(s))
    except ValueError:
        return s


def enrich_recommendation_rows(
    rows: list[dict[str, Any]],
    snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Attach mentor_profile_id, display name, tier, etc. from matchmaking snapshot."""
    if not snapshot or not rows:
        return rows
    by_uid: dict[str, dict[str, Any]] = {}
    for m in snapshot.get("mentors") or []:
        uid = m.get("user_id")
        if not uid:
            continue
        by_uid[_norm_uid(str(uid))] = m
    for r in rows:
        uid = _norm_uid(str(r.get("mentor_id", "")))
        m = by_uid.get(uid) if uid else None
        if not m:
            continue
        r["mentor_profile_id"] = m.get("mentor_profile_id")
        r["display_name"] = m.get("display_name")
        r["expertise_areas"] = m.get("expertise_areas") or []
        r["tier_id"] = m.get("tier")
        cost = m.get("session_credit_cost")
        if cost is not None:
            r["session_credit_cost"] = int(cost)
    return rows
