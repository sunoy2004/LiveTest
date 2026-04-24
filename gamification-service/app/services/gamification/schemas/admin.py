from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RuleUpdateBody(BaseModel):
    base_credit_value: int | None = None
    is_active: bool | None = None
    cooldown_seconds: int | None = Field(None, ge=0)


class AdminWalletBody(BaseModel):
    amount: int = Field(..., ge=1)
    idempotency_key: str = Field(..., min_length=1, max_length=512)


class ActivityRuleOut(BaseModel):
    rule_code: str
    transaction_type: str
    base_credit_value: int
    is_active: bool
    cooldown_seconds: int
