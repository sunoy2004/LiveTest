from __future__ import annotations
import logging
import os
from typing import Any
import httpx

log = logging.getLogger(__name__)

def fetch_matchmaking_snapshot() -> dict[str, Any] | None:
    # Now fetching from Mentoring Service instead of User Service
    base = os.getenv("MENTORING_SERVICE_URL") or os.getenv("USER_SERVICE_URL", "")
    base = base.rstrip("/")
    token = os.getenv("INTERNAL_API_TOKEN", "")
    
    if not base or not token:
        log.warning("MENTORING_SERVICE_URL or INTERNAL_API_TOKEN unset; snapshot empty")
        return None
        
    try:
        # Note: Added /api/v1/internal/matchmaking-snapshot path matching Mentoring Service route
        url = f"{base}/api/v1/internal/matchmaking-snapshot"
        r = httpx.get(
            url,
            headers={"X-Internal-Token": token},
            timeout=30.0,
        )
        if r.status_code != 200:
            log.warning("snapshot HTTP %s at %s", r.status_code, url)
            return None
            
        data: Any = r.json()
        if not isinstance(data, dict):
            log.warning("matchmaking snapshot response is not a JSON object")
            return None
            
        if not (data.get("mentors") or data.get("mentees")):
            log.warning("matchmaking snapshot is empty")
            
        return data
    except Exception as exc:
        log.warning("snapshot fetch failed: %s", exc)
        return None
