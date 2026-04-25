from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class LeaderboardItem(BaseModel):
    rank: int = Field(ge=1)
    user_id: UUID
    user_name: str | None = None
    score: int = Field(ge=0)


class LeaderboardListResponse(BaseModel):
    items: list[LeaderboardItem]


class LeaderboardMeResponse(BaseModel):
    item: LeaderboardItem

