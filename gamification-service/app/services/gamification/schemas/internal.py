from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class InternalTransactionBody(BaseModel):
    user_id: UUID
    rule_code: str
    amount: int | None = Field(default=None, ge=1)
    idempotency_key: str = Field(..., min_length=1, max_length=512)


class InternalDeductBody(BaseModel):
    user_id: UUID
    rule_code: str
    amount: int = Field(..., ge=1)
    idempotency_key: str = Field(..., min_length=1, max_length=512)
