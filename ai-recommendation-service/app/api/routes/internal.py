from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.services.bootstrap import run_full_reindex_from_user_service

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


@router.post("/matchmaking/reindex")
async def matchmaking_reindex(
    _: None = Depends(require_internal_token),
) -> dict[str, Any]:
    """
    Pull latest mentor/mentee rows from User Service snapshot, refresh the in-memory graph,
    and (when RECOMMENDATION_ENGINE=pgvector) re-embed and upsert match_profiles.
    Call this after seeding users or changing profiles so recommendations use current data.
    """
    result = await run_full_reindex_from_user_service()
    if not result.get("ok"):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("detail", "reindex_failed"),
        )
    return result
