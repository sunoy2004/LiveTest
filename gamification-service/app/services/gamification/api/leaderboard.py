from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.services.gamification.schemas.leaderboard import LeaderboardItem
from app.services.gamification.services.leaderboard_service import LeaderboardService

router = APIRouter(prefix="/api/v1/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardItem])
async def leaderboard_top(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[LeaderboardItem]:
    return await LeaderboardService(db).get_top_users(limit=limit)


@router.get("/me", response_model=LeaderboardItem)
async def leaderboard_me(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> LeaderboardItem:
    return await LeaderboardService(db).get_user_rank(user_id=user_id)


@router.get("/around-me", response_model=list[LeaderboardItem])
async def leaderboard_around_me(
    user_id: UUID = Depends(get_current_user_id),
    window: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[LeaderboardItem]:
    return await LeaderboardService(db).get_users_around(user_id=user_id, window=window)

