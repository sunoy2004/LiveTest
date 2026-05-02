from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text

from app.ai.factory import get_embedding_provider
from app.infra.db import get_session_factory
from app.infra.settings import get_settings
from app.services import recommendation_cache
from app.services.mentoring_snapshot import build_mentoring_snapshot
from app.services.profile_ingestion import upsert_from_snapshot

log = logging.getLogger(__name__)


def _db_hint() -> str:
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return "DATABASE_URL is unset"
    try:
        # postgresql+asyncpg://user:pass@host:port/dbname
        u = urlparse(raw.replace("+asyncpg", "", 1))
        name = (u.path or "").lstrip("/") or "?"
        host = u.hostname or u.netloc or "?"
        return f"db={name!r} host={host!r}"
    except Exception:
        return "DATABASE_URL present (parse failed)"


def describe_database_config() -> str:
    """
    Same DB URL SQLAlchemy uses (Settings.database_url ← Cloud Run env DATABASE_URL).
    Safe for logs — database name + host or Cloud SQL socket path.
    """
    from urllib.parse import parse_qs

    try:
        raw = get_settings().database_url.strip()
        if not raw:
            return "Settings.database_url is empty"
        u = urlparse(raw.replace("+asyncpg", "", 1))
        name = (u.path or "").lstrip("/") or "?"
        qs = parse_qs(u.query or "")
        sock = (qs.get("host") or [None])[0]
        if sock:
            return f"db={name!r} cloud_sql_socket={sock!r}"
        host = u.hostname or "?"
        port = f":{u.port}" if u.port else ""
        return f"db={name!r} tcp={host}{port}"
    except Exception as exc:
        return f"could not parse Settings.database_url ({exc})"


async def fetch_snapshot_from_local_db() -> dict:
    """Load mentor/mentee/connection rows from mentoring domain tables (same DB as match_profiles)."""
    fac = get_session_factory()
    async with fac() as session:
        return await build_mentoring_snapshot(session)


async def bootstrap_from_local_db() -> tuple[bool, str]:
    """
    Build embeddings from mentoring domain tables into match_profiles.
    Returns (success, message for logs).
    """
    try:
        snap = await fetch_snapshot_from_local_db()
        nm, ne = len(snap["mentors"]), len(snap["mentees"])
        if nm == 0 and ne == 0:
            return (
                False,
                f"no mentor/mentee rows in snapshot ({_db_hint()}); "
                "point DATABASE_URL at the same PostgreSQL database as the mentoring service "
                "and ensure mentor_profiles / mentee_profiles are populated",
            )

        prov = get_embedding_provider()
        fac = get_session_factory()
        async with fac() as session:
            n = await upsert_from_snapshot(session, prov, snap)
            await session.commit()
            log.info("Local bootstrap: match_profiles upserted: %d", n)

            cnt_r = await session.execute(text("SELECT COUNT(*) FROM match_profiles"))
            stored = int(cnt_r.scalar_one())
            if stored == 0 and n > 0:
                log.error(
                    "Bootstrap inconsistency: upsert reported %d rows but match_profiles count is 0",
                    n,
                )
            elif n > 0:
                log.info("match_profiles row count after bootstrap: %d", stored)

        if get_settings().recommendation_engine == "graph":
            from app.services.graph import graph_store

            graph_store.hydrate_from_snapshot(snap)

        await recommendation_cache.invalidate_all_recommendation_caches()
        return True, f"upserted {n} match_profiles ({nm} mentors, {ne} mentees in snapshot)"
    except Exception as e:
        log.exception("Bootstrap from local DB failed")
        return False, f"{type(e).__name__}: {e!s}"


async def run_bootstrap_with_retry() -> None:
    last_msg = ""
    for attempt in range(60):
        ok, last_msg = await bootstrap_from_local_db()
        if ok:
            log.info("Startup embedding bootstrap succeeded: %s", last_msg)
            return
        if attempt < 3 or attempt % 10 == 9:
            log.warning(
                "Startup embedding bootstrap attempt %s/60 failed: %s",
                attempt + 1,
                last_msg,
            )
        await asyncio.sleep(2)

    log.error(
        "Startup embedding bootstrap gave up after 60 attempts (~2 min). "
        "match_profiles may stay empty. Last error: %s. Check %s; "
        "run POST /internal/matchmaking/reindex with X-Internal-Token after fixing data/URL.",
        last_msg,
        _db_hint(),
    )


async def run_full_reindex_from_local_db() -> dict:
    snap = await fetch_snapshot_from_local_db()
    prov = get_embedding_provider()
    fac = get_session_factory()
    async with fac() as session:
        n_up = await upsert_from_snapshot(session, prov, snap)
        await session.commit()

    if get_settings().recommendation_engine == "graph":
        from app.services.graph import graph_store

        graph_store.hydrate_from_snapshot(snap)

    n_cache = await recommendation_cache.invalidate_all_recommendation_caches()
    return {
        "ok": True,
        "mentor_rows": len(snap["mentors"]),
        "mentee_rows": len(snap["mentees"]),
        "match_profiles_upserted": n_up,
        "recommendation_cache_keys_deleted": n_cache,
    }


async def rehydrate_from_user_service() -> bool:
    """
    Rebuild `match_profiles` from the mentoring database. Used when a mentee has no embedding row yet.
    """
    ok, _msg = await bootstrap_from_local_db()
    return ok


async def collect_matchmaking_diagnostics() -> dict[str, Any]:
    """
    Lightweight counts from the same DB as `match_profiles` (mentoring domain + AI tables).
    Use in /health and internal status — does not run embedding or full snapshot load.
    """
    out: dict[str, Any] = {
        "database_target": describe_database_config(),
    }
    fac = get_session_factory()
    try:
        async with fac() as session:
            for table in ("mentor_profiles", "mentee_profiles"):
                try:
                    r = await session.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    )
                    out[f"{table}_rows"] = int(r.scalar_one())
                except Exception as e:
                    out[f"{table}_error"] = f"{type(e).__name__}: {e!s}"[:240]

            try:
                r = await session.execute(text("SELECT COUNT(*) FROM match_profiles"))
                out["match_profiles_count"] = int(r.scalar_one())
            except Exception as e:
                out["match_profiles_error"] = f"{type(e).__name__}: {e!s}"[:240]

            try:
                r = await session.execute(
                    text(
                        """
                        SELECT role::text AS role, COUNT(*)::int AS n
                        FROM match_profiles
                        GROUP BY role
                        """
                    )
                )
                out["match_profiles_by_role"] = {
                    str(row[0]): int(row[1]) for row in r.fetchall()
                }
            except Exception as e:
                out["match_profiles_by_role_error"] = f"{type(e).__name__}: {e!s}"[:240]
    except Exception as e:
        out["diagnostics_error"] = f"{type(e).__name__}: {e!s}"[:400]

    mr = out.get("mentor_profiles_rows")
    me = out.get("mentee_profiles_rows")
    mp = out.get("match_profiles_count")
    if isinstance(mr, int) and isinstance(me, int) and mr == 0 and me == 0:
        out["hint"] = (
            "No rows in mentor_profiles/mentee_profiles on this DATABASE_URL. "
            "Use the same PostgreSQL database as mentoring-service, or seed profiles first."
        )
    elif (isinstance(mr, int) and mr > 0) or (isinstance(me, int) and me > 0):
        if mp == 0:
            out["hint"] = (
                "Mentoring profiles exist but match_profiles is empty: wait for startup embedding "
                "bootstrap or call POST /internal/matchmaking/reindex with X-Internal-Token."
            )

    return out
