"""Internal read-only access to activity rule definitions (for user-service pricing)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import require_internal_token
from app.services.gamification.models import ActivityRule

router = APIRouter(prefix="/internal", tags=["internal"])


class ActivityRuleRead(BaseModel):
    rule_code: str
    transaction_type: str
    base_credit_value: int = Field(ge=0)
    is_active: bool


@router.get("/activity-rules/{rule_code}", response_model=ActivityRuleRead)
async def get_activity_rule(
    rule_code: str,
    _: None = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
) -> ActivityRuleRead:
    res = await db.execute(select(ActivityRule).where(ActivityRule.rule_code == rule_code))
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown activity rule")
    return ActivityRuleRead(
        rule_code=row.rule_code,
        transaction_type=row.transaction_type,
        base_credit_value=row.base_credit_value,
        is_active=row.is_active,
    )
