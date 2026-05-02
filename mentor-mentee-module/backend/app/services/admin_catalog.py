"""Read/write catalog data for operator admin UI (JWT ADMIN role)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.connection_token import mentoring_connection_token


def _display_name(email: str | None, full_name: str | None) -> str:
    fn = (full_name or "").strip()
    if fn:
        return fn
    em = (email or "").strip()
    if "@" in em:
        local = em.split("@", 1)[0]
        return local.replace(".", " ").replace("_", " ").strip().title()
    return "User"


async def list_admin_mentors(session: AsyncSession) -> list[dict[str, Any]]:
    r = await session.execute(
        text(
            """
            SELECT mp.user_id::text AS id, u.email AS email,
                   COALESCE(NULLIF(TRIM(mp.full_name), ''), '') AS full_name,
                   COALESCE(mp.tier_id, 'PEER') AS tier
            FROM mentor_profiles mp
            INNER JOIN users u ON u.user_id = mp.user_id
            ORDER BY u.email ASC
            """
        )
    )
    rows = r.fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        uid, email, full_name, tier = row
        out.append(
            {
                "id": uid,
                "name": _display_name(email, full_name or None),
                "email": email or "",
                "tier": tier or "PEER",
                "base_credit_override": None,
            }
        )
    return out


async def list_admin_mentees(session: AsyncSession) -> list[dict[str, Any]]:
    r = await session.execute(
        text(
            """
            SELECT mp.user_id::text AS id, u.email AS email,
                   COALESCE(NULLIF(TRIM(mp.full_name), ''), '') AS full_name,
                   'ACTIVE'::text AS status
            FROM mentee_profiles mp
            INNER JOIN users u ON u.user_id = mp.user_id
            ORDER BY u.email ASC
            """
        )
    )
    out: list[dict[str, Any]] = []
    for row in r.fetchall():
        uid, email, full_name, status = row
        out.append(
            {
                "id": uid,
                "name": _display_name(email, full_name or None),
                "email": email or "",
                "status": status or "ACTIVE",
            }
        )
    return out


async def list_admin_connections(session: AsyncSession, limit: int = 500) -> list[dict[str, Any]]:
    r = await session.execute(
        text(
            """
            SELECT mc.mentor_user_id::text, mc.mentee_user_id::text,
                   um.email AS mentor_email, ue.email AS mentee_email,
                   COALESCE(mc.status, 'UNKNOWN') AS status
            FROM mentorship_connections mc
            INNER JOIN users um ON um.user_id = mc.mentor_user_id
            INNER JOIN users ue ON ue.user_id = mc.mentee_user_id
            ORDER BY um.email ASC, ue.email ASC
            LIMIT :lim
            """
        ),
        {"lim": limit},
    )
    out: list[dict[str, Any]] = []
    for row in r.fetchall():
        mid, meid, memail, meemail, st = row
        tok = mentoring_connection_token(uuid.UUID(mid), uuid.UUID(meid))
        out.append(
            {
                "connection_id": tok,
                "mentor_profile_id": mid,
                "mentee_profile_id": meid,
                "mentor_user_id": mid,
                "mentee_user_id": meid,
                "mentor_email": memail or "",
                "mentee_email": meemail or "",
                "status": st or "",
            }
        )
    return out


async def list_admin_sessions(session: AsyncSession) -> list[dict[str, Any]]:
    r = await session.execute(
        text(
            """
            SELECT s.session_id::text,
                   COALESCE(s.connection_id::text, '') AS connection_id,
                   um.email AS mentor_email, ue.email AS mentee_email,
                   s.start_time, s.status,
                   COALESCE(mt.session_credit_cost, 0) AS price
            FROM sessions s
            INNER JOIN users um ON um.user_id = s.mentor_user_id
            INNER JOIN users ue ON ue.user_id = s.mentee_user_id
            LEFT JOIN mentor_profiles mp ON mp.user_id = s.mentor_user_id
            LEFT JOIN mentor_tiers mt ON mt.tier_id = COALESCE(mp.tier_id, 'PEER')
            ORDER BY s.start_time DESC NULLS LAST, s.created_at DESC NULLS LAST
            LIMIT 500
            """
        )
    )
    out: list[dict[str, Any]] = []
    for row in r.fetchall():
        sid, conn_id, memail, meemail, start, st, price = row
        out.append(
            {
                "session_id": sid,
                "connection_id": conn_id or "",
                "mentor_name": _display_name(memail, None),
                "mentee_name": _display_name(meemail, None),
                "start_time": start.isoformat() if isinstance(start, datetime) else str(start or ""),
                "status": (st or "").upper() or "UNKNOWN",
                "price": int(price or 0),
            }
        )
    return out


async def list_admin_disputes(session: AsyncSession) -> list[dict[str, Any]]:
    r = await session.execute(
        text(
            """
            SELECT r.id::text, r.status, r.kind, r.session_id::text,
                   r.opened_by_user_id::text, r.payload, r.created_at, r.resolved_at
            FROM reports_and_disputes r
            ORDER BY r.created_at DESC NULLS LAST
            LIMIT 200
            """
        )
    )
    out: list[dict[str, Any]] = []
    for row in r.fetchall():
        rid, st, kind, sess_id, opener, payload, created_at, resolved_at = row
        reason = kind
        if isinstance(payload, dict) and payload.get("reason"):
            reason = str(payload["reason"])
        out.append(
            {
                "id": rid,
                "status": st or "OPEN",
                "kind": kind or "OTHER",
                "session_id": sess_id,
                "reason": reason,
                "opened_by_user_id": opener,
                "created_at": created_at.isoformat() if isinstance(created_at, datetime) else "",
                "resolved_at": resolved_at.isoformat() if isinstance(resolved_at, datetime) else None,
                "credits_associated": None,
            }
        )
    return out


async def resolve_admin_dispute(session: AsyncSession, dispute_id: uuid.UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE reports_and_disputes
            SET status = 'RESOLVED',
                resolved_at = :ts
            WHERE id = :rid AND UPPER(TRIM(COALESCE(status,''))) = 'OPEN'
            """
        ),
        {"rid": dispute_id, "ts": datetime.now(timezone.utc)},
    )


async def update_mentor_tier(
    session: AsyncSession,
    *,
    mentor_user_id: uuid.UUID,
    tier_id: str,
) -> dict[str, Any]:
    chk = await session.execute(
        text("SELECT 1 FROM mentor_tiers WHERE tier_id = :tid LIMIT 1"),
        {"tid": tier_id},
    )
    if chk.scalar_one_or_none() is None:
        raise ValueError(f"Unknown tier_id: {tier_id}")

    await session.execute(
        text(
            """
            UPDATE mentor_profiles
            SET tier_id = :tid
            WHERE user_id = :uid
            """
        ),
        {"tid": tier_id, "uid": mentor_user_id},
    )
    return {"mentor_profile_id": str(mentor_user_id), "tier": tier_id, "base_credit_override": None}
