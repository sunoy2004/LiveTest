from __future__ import annotations

import logging
from typing import Any

from app.infra.db import get_session_factory
from app.services.mentoring_snapshot import build_mentoring_snapshot

log = logging.getLogger(__name__)


async def fetch_matchmaking_snapshot() -> dict[str, Any] | None:
    """
    Load mentor/mentee profile data from mentoring domain tables (same PostgreSQL DB as match_profiles).

    No HTTP hop — uses `DATABASE_URL` pointing at the `mentoring` database alongside the mentoring service.
    """
    try:
        fac = get_session_factory()
        async with fac() as session:
            return await build_mentoring_snapshot(session)
    except Exception as exc:
        log.warning("matchmaking snapshot from mentoring DB failed: %s", exc)
        return None
