"""Operator admin API — mentoring database authority; requires JWT with ADMIN role."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.services.admin_catalog import (
    list_admin_connections,
    list_admin_disputes,
    list_admin_mentees,
    list_admin_mentors,
    list_admin_sessions,
    resolve_admin_dispute,
    update_mentor_tier,
)

router = APIRouter()


class MentorPricingBody(BaseModel):
    tier: str = Field(..., description="mentor_tiers.tier_id: PEER | PROFESSIONAL | EXPERT")
    base_credit_override: int | None = Field(
        default=None,
        description="Reserved — session cost is driven by gamification BOOK_MENTOR_SESSION + tier; not persisted yet.",
    )


@router.get("/mentors")
async def admin_get_mentors(
    _: Annotated[None, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await list_admin_mentors(db)


@router.get("/mentees")
async def admin_get_mentees(
    _: Annotated[None, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await list_admin_mentees(db)


@router.get("/connections")
async def admin_get_connections(
    _: Annotated[None, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(500, ge=1, le=2000),
) -> list[dict[str, Any]]:
    return await list_admin_connections(db, limit=limit)


@router.get("/sessions")
async def admin_get_sessions(
    _: Annotated[None, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await list_admin_sessions(db)


@router.get("/disputes")
async def admin_get_disputes(
    _: Annotated[None, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await list_admin_disputes(db)


@router.post("/disputes/{dispute_id}/resolve")
async def admin_resolve_dispute_route(
    dispute_id: uuid.UUID,
    _: Annotated[None, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await resolve_admin_dispute(db, dispute_id)
    await db.commit()
    return {"status": "ok"}


@router.put("/mentor/{mentor_user_id}")
async def admin_put_mentor_pricing(
    mentor_user_id: uuid.UUID,
    body: MentorPricingBody,
    _: Annotated[None, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    tid = body.tier.strip().upper()
    if tid not in ("PEER", "PROFESSIONAL", "EXPERT"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tier must be PEER, PROFESSIONAL, or EXPERT",
        )
    try:
        out = await update_mentor_tier(db, mentor_user_id=mentor_user_id, tier_id=tid)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await db.commit()
    return out
