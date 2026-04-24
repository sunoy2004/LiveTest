from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)


def fetch_matchmaking_snapshot() -> dict[str, Any] | None:
    base = os.getenv("USER_SERVICE_URL", "").rstrip("/")
    token = os.getenv("INTERNAL_API_TOKEN", "")
    if not base or not token:
        log.warning("USER_SERVICE_URL or INTERNAL_API_TOKEN unset; snapshot empty")
        return None
    try:
        r = httpx.get(
            f"{base}/internal/matchmaking/snapshot",
            headers={"X-Internal-Token": token},
            timeout=30.0,
        )
        if r.status_code != 200:
            log.warning("snapshot HTTP %s", r.status_code)
            return None
        data: Any = r.json()
        if not isinstance(data, dict):
            log.warning("matchmaking snapshot response is not a JSON object")
            return None
        if not (data.get("mentors") or data.get("mentees")):
            log.warning("matchmaking snapshot is empty: user service returned no mentors and no mentees")
        return data
    except Exception as exc:  # noqa: BLE001
        log.warning("snapshot fetch failed: %s", exc)
        return None
