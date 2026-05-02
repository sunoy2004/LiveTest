from __future__ import annotations
import os
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from app.services.bootstrap import (
    collect_matchmaking_diagnostics,
    run_full_reindex_from_local_db,
)

router = APIRouter(prefix="/internal", tags=["internal"])

INTERNAL_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")

def require_internal_token(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
) -> None:
    if not INTERNAL_TOKEN or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Invalid internal token",
        )

@router.get("/matchmaking/status")
async def matchmaking_status(
    _: None = Depends(require_internal_token),
) -> dict[str, Any]:
    """
    Row counts for mentoring domain tables vs match_profiles (no embedding work).
    If mentor_profiles/mentee_profiles have rows but match_profiles is empty, run POST /internal/matchmaking/reindex.
    """
    return await collect_matchmaking_diagnostics()


@router.post("/matchmaking/reindex")
async def matchmaking_reindex(
    _: None = Depends(require_internal_token),
) -> dict[str, Any]:
    """
    Directly re-index AI match_profiles by querying the local mentoring database tables.
    Call this after seeding users or changing profiles to refresh recommendations.
    """
    result = await run_full_reindex_from_local_db()
    if not result.get("ok"):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("detail", "reindex_failed"),
        )
    return result
