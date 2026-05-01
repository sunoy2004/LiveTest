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


def _safe_columns(sync_conn, table: str) -> set[str]:
    try:
        return {c["name"] for c in inspect(sync_conn).get_columns(table)}
    except Exception:
        return set()


async def _table_columns(session: AsyncSession) -> tuple[set[str], set[str]]:
    def _probe(sync_conn) -> tuple[set[str], set[str]]:
        return (
            _safe_columns(sync_conn, "mentor_profiles"),
            _safe_columns(sync_conn, "mentee_profiles"),
        )

    return await session.run_sync(_probe)


async def build_mentoring_snapshot(session: AsyncSession) -> dict[str, Any]:
    mp_cols, me_cols = await _table_columns(session)
    now = datetime.now(timezone.utc).isoformat()

    if not mp_cols or not me_cols:
        log.warning(
            "mentoring_snapshot: mentor_profiles or mentee_profiles missing or empty schema "
            "(mentor_cols=%s mentee_cols=%s)",
            bool(mp_cols),
            bool(me_cols),
        )

    mentors: list[dict[str, Any]] = []
    if mp_cols:
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
            if has_tier:
                q = text(
                    f"""
                    SELECT mp.user_id::text, {bio_sql}, mp.{exp_col}, {ey_sql},
                           u.email, {fn_sql},
                           COALESCE(mt.session_credit_cost, peer.session_credit_cost, 0),
                           COALESCE(mp.tier_id::text, 'PEER')
                    FROM mentor_profiles mp
                    INNER JOIN users u ON u.user_id = mp.user_id
                    LEFT JOIN mentor_tiers peer ON peer.tier_id = 'PEER'
                    LEFT JOIN mentor_tiers mt ON mt.tier_id = mp.tier_id
                    """
                )
            else:
                q = text(
                    f"""
                    SELECT mp.user_id::text, {bio_sql}, mp.{exp_col}, {ey_sql},
                           u.email, {fn_sql},
                           COALESCE(peer.session_credit_cost, 0),
                           'PEER'::text
                    FROM mentor_profiles mp
                    INNER JOIN users u ON u.user_id = mp.user_id
                    LEFT JOIN mentor_tiers peer ON peer.tier_id = 'PEER'
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
                log.warning("mentoring_snapshot mentor query failed: %s", e)
        else:
            log.warning(
                "mentoring_snapshot: mentor_profiles has no expertise / expertise_areas; skipping mentors"
            )

    mentees: list[dict[str, Any]] = []
    if me_cols and "learning_goals" in me_cols:
        has_me_fn = "full_name" in me_cols
        edu_sql = "m.education_level" if "education_level" in me_cols else "NULL::text"
        fn_sql = "m.full_name" if has_me_fn else "NULL::text"
        q_me = text(
            f"""
            SELECT m.user_id::text, m.learning_goals, {edu_sql}, u.email, {fn_sql}
            FROM mentee_profiles m
            INNER JOIN users u ON u.user_id = m.user_id
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
            log.warning("mentoring_snapshot mentee query failed: %s", e)

    connections: list[dict[str, str]] = []
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
            {"mentor_id": str(r[0]), "mentee_id": str(r[1])} for r in con_res.fetchall()
        ]
    except Exception as e:
        log.warning("mentoring_snapshot connections query failed: %s", e)

    return {
        "mentors": mentors,
        "mentees": mentees,
        "connections": connections,
        "timestamp": now,
    }
