from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.gamification.constants import BOOKING_SPEND, LEGACY_CREDIT_ADD
from app.services.gamification.events.publisher import publish_credit_score_updated
from app.services.gamification.schemas.payloads import (
    LegacyAddRequest,
    LegacyBalanceResponse,
    LegacyDeductRequest,
    LegacyDeductResponse,
    ProcessTransactionPayload,
)
from app.services.gamification.api.errors import raise_http
from app.services.gamification.models import Wallet
from app.services.gamification.services.exceptions import GamificationError, InsufficientFundsError
from app.services.gamification.services.ledger_engine import process_transaction

router = APIRouter(tags=["legacy"])


@router.get("/balance/{user_id}", response_model=LegacyBalanceResponse)
async def legacy_balance(user_id: str, db: AsyncSession = Depends(get_db)) -> LegacyBalanceResponse:
    from uuid import UUID

    uid = UUID(user_id)
    res = await db.execute(select(Wallet).where(Wallet.user_id == uid))
    w = res.scalar_one_or_none()
    bal = w.current_balance if w else 0
    return LegacyBalanceResponse(user_id=uid, balance=bal, xp=0)


@router.post("/deduct", response_model=LegacyDeductResponse)
async def legacy_deduct(
    body: LegacyDeductRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> LegacyDeductResponse:
    payload = ProcessTransactionPayload(
        user_id=body.user_id,
        rule_code=BOOKING_SPEND,
        amount=body.amount,
        idempotency_key=f"legacy:deduct:{uuid4()}",
    )
    try:
        out = await process_transaction(db, payload)
    except InsufficientFundsError:
        res = await db.execute(select(Wallet).where(Wallet.user_id == body.user_id))
        w = res.scalar_one_or_none()
        bal = w.current_balance if w else 0
        return LegacyDeductResponse(ok=False, balance=bal, xp=0)
    except GamificationError as e:
        raise_http(e)
    if not out.idempotent_replay:
        background_tasks.add_task(
            publish_credit_score_updated,
            user_id=out.user_id,
            balance=out.balance_after,
            transaction_id=str(out.transaction_id),
        )
    return LegacyDeductResponse(ok=True, balance=out.balance_after, xp=0)


@router.post("/add", response_model=LegacyBalanceResponse)
async def legacy_add(
    body: LegacyAddRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> LegacyBalanceResponse:
    payload = ProcessTransactionPayload(
        user_id=body.user_id,
        rule_code=LEGACY_CREDIT_ADD,
        amount=body.amount,
        idempotency_key=f"legacy:add:{uuid4()}",
    )
    try:
        out = await process_transaction(db, payload)
    except GamificationError as e:
        raise_http(e)
    if not out.idempotent_replay:
        background_tasks.add_task(
            publish_credit_score_updated,
            user_id=out.user_id,
            balance=out.balance_after,
            transaction_id=str(out.transaction_id),
        )
    return LegacyBalanceResponse(user_id=body.user_id, balance=out.balance_after, xp=0)
