"""Read/write catalog data for operator admin UI (JWT ADMIN role).

Queries adapt to schema drift: some DBs were created from Alembic 001 (e.g. reports `id`,
`mentor_profiles.full_name`) and others from SQLAlchemy models (`report_id`, `bio`, no `tier_id`).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.connection_token import mentoring_connection_token

# Cached per process — physical column names in `public` (see `_columns`).
_col_cache: dict[str, frozenset[str]] = {}


async def _columns(session: AsyncSession, table: str) -> frozenset[str]:
    """Resolve actual columns on `public.<table>` (PostgreSQL: pg_catalog first)."""
    if table not in _col_cache:
        names: set[str] = set()
        try:
            r = await session.execute(
                text(
                    """
                    SELECT a.attname::text
                    FROM pg_catalog.pg_attribute a
                    INNER JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
                    INNER JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
                    WHERE n.nspname = 'public'
                      AND c.relname = :t
                      AND c.relkind IN ('r', 'p', 'v', 'm')
                      AND a.attnum > 0
                      AND NOT a.attisdropped
                    """
                ),
                {"t": table},
            )
            names = {row[0] for row in r.fetchall()}
        except Exception:
            names = set()
        if not names:
            r2 = await session.execute(
                text(
                    """
                    SELECT column_name::text
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = :t
                    """
                ),
                {"t": table},
            )
            names = {row[0] for row in r2.fetchall()}
        _col_cache[table] = frozenset(names)
    return _col_cache[table]


def _display_name(email: str | None, full_name: str | None) -> str:
    fn = (full_name or "").strip()
    if fn:
        return fn
    em = (email or "").strip()
    if "@" in em:
        local = em.split("@", 1)[0]
        return local.replace(".", " ").replace("_", " ").strip().title()
    return "User"


def _mentor_display_name_expr(mp_cols: frozenset[str]) -> str:
    """Only reference columns present on disk — ORM-shaped DBs use `bio`, not `full_name`."""
    has_fn = "full_name" in mp_cols
    has_bio = "bio" in mp_cols
    if has_bio and has_fn:
        return (
            "COALESCE(NULLIF(TRIM(mp.bio::text), ''), "
            "NULLIF(TRIM(mp.full_name::text), ''), '')"
        )
    if has_bio:
        return "COALESCE(NULLIF(TRIM(mp.bio::text), ''), '')"
    if has_fn:
        return "COALESCE(NULLIF(TRIM(mp.full_name::text), ''), '')"
    return "''::text"


def _mentor_tier_expr(mp_cols: frozenset[str]) -> str:
    if "tier_id" in mp_cols:
        return "COALESCE(mp.tier_id::text, 'PEER')"
    return "'PEER'::text"


async def list_admin_mentors(session: AsyncSession) -> list[dict[str, Any]]:
    mp_cols = await _columns(session, "mentor_profiles")
    name_sql = _mentor_display_name_expr(mp_cols)
    tier_sql = _mentor_tier_expr(mp_cols)
    r = await session.execute(
        text(
            f"""
            SELECT mp.user_id::text AS id, u.email AS email,
                   {name_sql} AS full_name,
                   {tier_sql} AS tier
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


def _mentee_display_name_expr(mp_cols: frozenset[str]) -> str:
    if "full_name" in mp_cols:
        return "COALESCE(NULLIF(TRIM(mp.full_name::text), ''), '')"
    return "''::text"


async def list_admin_mentees(session: AsyncSession) -> list[dict[str, Any]]:
    mp_cols = await _columns(session, "mentee_profiles")
    name_sql = _mentee_display_name_expr(mp_cols)
    r = await session.execute(
        text(
            f"""
            SELECT mp.user_id::text AS id, u.email AS email,
                   {name_sql} AS full_name,
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


def _sessions_tier_join(mp_cols: frozenset[str]) -> str:
    if "tier_id" in mp_cols:
        return (
            "LEFT JOIN mentor_profiles mp ON mp.user_id = s.mentor_user_id "
            "LEFT JOIN mentor_tiers mt ON mt.tier_id = COALESCE(mp.tier_id, 'PEER')"
        )
    return "LEFT JOIN mentor_tiers mt ON mt.tier_id = 'PEER'"


async def list_admin_sessions(session: AsyncSession) -> list[dict[str, Any]]:
    sess_cols = await _columns(session, "sessions")
    mc_cols = await _columns(session, "mentorship_connections")
    mp_cols = await _columns(session, "mentor_profiles")

    conn_sel = (
        "COALESCE(s.connection_id::text, '')" if "connection_id" in sess_cols else "''::text"
    )
    start_sel = "s.start_time"
    if "start_time" not in sess_cols:
        start_sel = "s.created_at" if "created_at" in sess_cols else "NULL::timestamptz"

    order_parts: list[str] = []
    if "start_time" in sess_cols:
        order_parts.append("s.start_time DESC NULLS LAST")
    if "created_at" in sess_cols:
        order_parts.append("s.created_at DESC NULLS LAST")
    order_sql = ", ".join(order_parts) if order_parts else "s.session_id"

    tier_join = _sessions_tier_join(mp_cols)

    if "mentor_user_id" in sess_cols and "mentee_user_id" in sess_cols:
        sql = f"""
            SELECT s.session_id::text,
                   {conn_sel} AS connection_id,
                   um.email AS mentor_email, ue.email AS mentee_email,
                   {start_sel} AS start_time, s.status,
                   COALESCE(mt.session_credit_cost, 0) AS price
            FROM sessions s
            INNER JOIN users um ON um.user_id = s.mentor_user_id
            INNER JOIN users ue ON ue.user_id = s.mentee_user_id
            {tier_join}
            ORDER BY {order_sql}
            LIMIT 500
            """
    elif (
        "connection_id" in sess_cols
        and "connection_id" in mc_cols
        and "mentor_user_id" in mc_cols
        and "mentee_user_id" in mc_cols
    ):
        tier_join_mc = (
            "LEFT JOIN mentor_profiles mp ON mp.user_id = mc.mentor_user_id "
            "LEFT JOIN mentor_tiers mt ON mt.tier_id = COALESCE(mp.tier_id, 'PEER')"
            if "tier_id" in mp_cols
            else "LEFT JOIN mentor_tiers mt ON mt.tier_id = 'PEER'"
        )
        sql = f"""
            SELECT s.session_id::text,
                   COALESCE(s.connection_id::text, '') AS connection_id,
                   um.email AS mentor_email, ue.email AS mentee_email,
                   {start_sel} AS start_time, s.status,
                   COALESCE(mt.session_credit_cost, 0) AS price
            FROM sessions s
            INNER JOIN mentorship_connections mc ON mc.connection_id = s.connection_id
            INNER JOIN users um ON um.user_id = mc.mentor_user_id
            INNER JOIN users ue ON ue.user_id = mc.mentee_user_id
            {tier_join_mc}
            ORDER BY {order_sql}
            LIMIT 500
            """
    else:
        return []

    r = await session.execute(text(sql))
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
    cols = await _columns(session, "reports_and_disputes")
    if not cols:
        return []

    pk = "report_id" if "report_id" in cols else "id"
    if pk not in cols:
        return []

    kind_sel = "r.kind::text" if "kind" in cols else "'OTHER'::text"
    sess_sel = "r.session_id::text" if "session_id" in cols else "NULL::text"
    if "opened_by_user_id" in cols:
        opener_sel = "r.opened_by_user_id::text"
    elif "raised_by_user_id" in cols:
        opener_sel = "r.raised_by_user_id::text"
    else:
        opener_sel = "NULL::text"
    payload_sel = "r.payload" if "payload" in cols else "NULL::jsonb"
    created_sel = "r.created_at" if "created_at" in cols else "NULL::timestamptz"
    resolved_sel = "r.resolved_at" if "resolved_at" in cols else "NULL::timestamptz"
    reason_sel = "r.reason::text" if "reason" in cols else "NULL::text"

    order_sel = "r.created_at DESC NULLS LAST" if "created_at" in cols else f"r.{pk} DESC"

    sql = f"""
        SELECT r.{pk}::text, r.status, {kind_sel}, {sess_sel},
               {opener_sel}, {payload_sel}, {created_sel}, {resolved_sel}, {reason_sel}
        FROM reports_and_disputes r
        ORDER BY {order_sel}
        LIMIT 200
        """
    r = await session.execute(text(sql))
    out: list[dict[str, Any]] = []
    for row in r.fetchall():
        rid, st, kind, sess_id, opener, payload, created_at, resolved_at, reason_txt = row
        reason = str(kind).strip() if kind not in (None, "") else "OTHER"
        if isinstance(payload, dict) and payload.get("reason"):
            reason = str(payload["reason"])
        elif reason_txt and str(reason_txt).strip():
            reason = str(reason_txt).strip()

        out.append(
            {
                "id": rid,
                "status": st or "OPEN",
                "kind": (str(kind) if kind not in (None, "") else "OTHER"),
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
    cols = await _columns(session, "reports_and_disputes")
    pk = "report_id" if "report_id" in cols else "id"
    if pk not in cols:
        return

    sets = ["status = 'RESOLVED'"]
    params: dict[str, Any] = {"rid": dispute_id}
    if "resolved_at" in cols:
        sets.append("resolved_at = :ts")
        params["ts"] = datetime.now(timezone.utc)

    sql = f"""
        UPDATE reports_and_disputes
        SET {", ".join(sets)}
        WHERE {pk} = :rid AND UPPER(TRIM(COALESCE(status,''))) = 'OPEN'
        """
    await session.execute(text(sql), params)


async def update_mentor_tier(
    session: AsyncSession,
    *,
    mentor_user_id: uuid.UUID,
    tier_id: str,
) -> dict[str, Any]:
    mp_cols = await _columns(session, "mentor_profiles")
    if "tier_id" not in mp_cols:
        raise ValueError(
            "This database has no mentor_profiles.tier_id column; run Alembic migrations "
            "or add the column before changing tiers in admin."
        )

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
