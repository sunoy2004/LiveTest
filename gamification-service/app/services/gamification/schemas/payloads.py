from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ProcessTransactionPayload(BaseModel):
    user_id: UUID
    rule_code: str
    amount: int | None = None
    idempotency_key: str = Field(..., min_length=1, max_length=512)


class TransactionResult(BaseModel):
    transaction_id: UUID
    user_id: UUID
    rule_code: str
    amount: int
    balance_after: int
    lifetime_earned: int | None = None
    idempotent_replay: bool = False


class WalletPublic(BaseModel):
    user_id: UUID
    current_balance: int
    lifetime_earned: int


class LedgerItem(BaseModel):
    transaction_id: UUID
    rule_code: str
    amount: int
    balance_after: int
    created_at: str


class LegacyBalanceResponse(BaseModel):
    user_id: UUID
    balance: int
    xp: int = 0


class LegacyDeductRequest(BaseModel):
    user_id: UUID
    amount: int = Field(ge=1)


class LegacyDeductResponse(BaseModel):
    ok: bool
    balance: int
    xp: int = 0


class LegacyAddRequest(BaseModel):
    user_id: UUID
    amount: int = Field(ge=1)
    xp: int = 0

