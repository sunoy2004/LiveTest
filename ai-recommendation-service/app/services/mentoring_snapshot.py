"""
Build the matchmaking snapshot from mentoring domain tables in the same database as `match_profiles`.

Reads `mentor_profiles`, `mentee_profiles`, `users`, `mentor_tiers`, and `mentorship_connections`
so the AI service can ingest embeddings and enrich recommendations without HTTP calls to the
mentoring API.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


def _display_name(email: str | None, full_name: str | None) -> str:
    fn = (full_name or "").strip()
    if fn:
        return fn
    em = (email or "").strip()
    if "@" in em:
        return em.split("@")[0].replace(".", " ").replace("_", " ").strip().title()
    return ""


def _inspector(sync_session):
    """AsyncSession.run_sync passes a sync ORM Session, not a Connection — inspect the engine."""
    return inspect(sync_session.get_bind())


def _safe_columns(sync_session, table: str) -> set[str]:
    try:
        return {c["name"] for c in _inspector(sync_session).get_columns(table)}
    except Exception:
        return set()


async def _table_names(session: AsyncSession) -> set[str]:
    def _names(sync_session) -> set[str]:
        return set(_inspector(sync_session).get_table_names())

    return await session.run_sync(_names)


async def _table_columns(session: AsyncSession) -> tuple[set[str], set[str]]:
    def _probe(sync_session) -> tuple[set[str], set[str]]:
        return (
            _safe_columns(sync_session, "mentor_profiles"),
            _safe_columns(sync_session, "mentee_profiles"),
        )

    return await session.run_sync(_probe)


async def build_mentoring_snapshot(session: AsyncSession) -> dict[str, Any]:
    tables = await _table_names(session)
    mp_cols, me_cols = await _table_columns(session)
    now = datetime.now(timezone.utc).isoformat()

    has_users = "users" in tables
    has_tier_table = "mentor_tiers" in tables
    if "mentor_profiles" not in tables:
        log.warning("mentoring_snapshot: table mentor_profiles not found (wrong DATABASE_URL / DB?)")
    if "mentee_profiles" not in tables:
        log.warning("mentoring_snapshot: table mentee_profiles not found (wrong DATABASE_URL / DB?)")

    if not mp_cols:
        log.warning("mentoring_snapshot: cannot read columns for mentor_profiles")
    if not me_cols:
        log.warning("mentoring_snapshot: cannot read columns for mentee_profiles")

    mentors: list[dict[str, Any]] = []
    if mp_cols and "mentor_profiles" in tables:
        exp_col = (
            "expertise"
            if "expertise" in mp_cols
            else ("expertise_areas" if "expertise_areas" in mp_cols else None)
        )
        has_tier = "tier_id" in mp_cols
        has_m_fn = "full_name" in mp_cols
        has_exp_y = "experience_years" in mp_cols
        has_bio = "bio" in mp_cols
        bio_sql = "mp.bio" if has_bio else "NULL::text"

        if exp_col:
            ey_sql = "mp.experience_years" if has_exp_y else "NULL::integer"
            fn_sql = "mp.full_name" if has_m_fn else "NULL::text"
            user_email = "u.email" if has_users else "NULL::text"
            join_users = (
                "LEFT JOIN users u ON u.user_id = mp.user_id" if has_users else ""
            )

            if has_tier_table and has_tier:
                cost_expr = "COALESCE(mt.session_credit_cost, peer.session_credit_cost, 0)"
                tier_expr = "COALESCE(mp.tier_id::text, 'PEER')"
                tier_joins = """
                    LEFT JOIN mentor_tiers peer ON peer.tier_id = 'PEER'
                    LEFT JOIN mentor_tiers mt ON mt.tier_id = mp.tier_id
                """
            elif has_tier_table:
                cost_expr = "COALESCE(peer.session_credit_cost, 0)"
                tier_expr = "'PEER'::text"
                tier_joins = "LEFT JOIN mentor_tiers peer ON peer.tier_id = 'PEER'"
            else:
                cost_expr = "0"
                tier_expr = "'PEER'::text"
                tier_joins = ""

            q = text(
                f"""
                SELECT mp.user_id::text, {bio_sql}, mp.{exp_col}, {ey_sql},
                       {user_email}, {fn_sql},
                       ({cost_expr})::integer,
                       {tier_expr}
                FROM mentor_profiles mp
                {join_users}
                {tier_joins}
                """
            )
            try:
                res = await session.execute(q)
                for row in res.fetchall():
                    uid, bio, tags, exp_y, email, mfn, cost, tier_slug = row
                    tags_list = list(tags) if tags is not None else []
                    mentors.append(
                        {
                            "user_id": uid,
                            "bio": bio,
                            "expertise": tags_list,
                            "expertise_areas": tags_list,
                            "experience_years": exp_y,
                            "display_name": _display_name(email, mfn),
                            "tier": tier_slug,
                            "session_credit_cost": int(cost) if cost is not None else 0,
                        }
                    )
            except Exception as e:
                log.exception("mentoring_snapshot mentor query failed; trying minimal fallback: %s", e)
                mentors = await _fallback_mentors_minimal(session, mp_cols, exp_col)
        else:
            log.warning(
                "mentoring_snapshot: mentor_profiles has no expertise / expertise_areas; skipping mentors"
            )

    mentees: list[dict[str, Any]] = []
    if (
        me_cols
        and "mentee_profiles" in tables
        and "learning_goals" in me_cols
    ):
        has_me_fn = "full_name" in me_cols
        edu_sql = "m.education_level" if "education_level" in me_cols else "NULL::text"
        fn_sql = "m.full_name" if has_me_fn else "NULL::text"
        user_email = "u.email" if has_users else "NULL::text"
        join_users = (
            "LEFT JOIN users u ON u.user_id = m.user_id" if has_users else ""
        )
        q_me = text(
            f"""
            SELECT m.user_id::text, m.learning_goals, {edu_sql}, {user_email}, {fn_sql}
            FROM mentee_profiles m
            {join_users}
            """
        )
        try:
            res = await session.execute(q_me)
            for row in res.fetchall():
                uid, goals, edu, email, mfn = row
                goals_list = list(goals) if goals is not None else []
                mentees.append(
                    {
                        "user_id": uid,
                        "learning_goals": goals_list,
                        "education_level": edu or "",
                        "display_name": _display_name(email, mfn),
                    }
                )
        except Exception as e:
            log.exception("mentoring_snapshot mentee query failed: %s", e)

    connections: list[dict[str, str]] = []
    if "mentorship_connections" in tables:
        try:
            con_res = await session.execute(
                text(
                    """
                    SELECT mentor_user_id::text, mentee_user_id::text
                    FROM mentorship_connections
                    WHERE status = 'ACTIVE'
                    """
                )
            )
            connections = [
                {"mentor_id": str(r[0]), "mentee_id": str(r[1])}
                for r in con_res.fetchall()
            ]
        except Exception as e:
            log.warning("mentoring_snapshot connections query failed: %s", e)

    log.info(
        "mentoring_snapshot: mentors=%d mentees=%d connections=%d (has_users=%s has_tier_table=%s)",
        len(mentors),
        len(mentees),
        len(connections),
        has_users,
        has_tier_table,
    )

    return {
        "mentors": mentors,
        "mentees": mentees,
        "connections": connections,
        "timestamp": now,
    }


async def _fallback_mentors_minimal(
    session: AsyncSession,
    mp_cols: set[str],
    exp_col: str,
) -> list[dict[str, Any]]:
    """Last resort: no joins so a broken FK or missing tier table cannot zero out mentors."""
    has_bio = "bio" in mp_cols
    bio_sql = "mp.bio" if has_bio else "NULL::text"
    has_exp_y = "experience_years" in mp_cols
    ey_sql = "mp.experience_years" if has_exp_y else "NULL::integer"
    q = text(
        f"""
        SELECT mp.user_id::text, {bio_sql}, mp.{exp_col}, {ey_sql}
        FROM mentor_profiles mp
        """
    )
    out: list[dict[str, Any]] = []
    try:
        res = await session.execute(q)
        for row in res.fetchall():
            uid, bio, tags, exp_y = row
            tags_list = list(tags) if tags is not None else []
            out.append(
                {
                    "user_id": uid,
                    "bio": bio,
                    "expertise": tags_list,
                    "expertise_areas": tags_list,
                    "experience_years": exp_y,
                    "display_name": "",
                    "tier": "PEER",
                    "session_credit_cost": 0,
                }
            )
        log.info("mentoring_snapshot: fallback mentor rows=%d", len(out))
    except Exception as e:
        log.exception("mentoring_snapshot fallback mentor query failed: %s", e)
    return out
