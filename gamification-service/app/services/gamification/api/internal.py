from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import require_internal_token
from app.services.gamification.events.publisher import publish_credit_score_updated
from app.services.gamification.schemas.internal import InternalDeductBody, InternalTransactionBody
from app.services.gamification.schemas.payloads import ProcessTransactionPayload, TransactionResult
from app.services.gamification.api.errors import raise_http
from app.services.gamification.services.exceptions import GamificationError
from app.services.gamification.services.ledger_engine import process_transaction

router = APIRouter(prefix="/internal/transactions", tags=["internal"])


@router.post("/deduct", response_model=TransactionResult)
async def internal_deduct(
    body: InternalDeductBody,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
) -> TransactionResult:
    payload = ProcessTransactionPayload(
        user_id=body.user_id,
        rule_code=body.rule_code,
        amount=body.amount,
        idempotency_key=body.idempotency_key,
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
            lifetime_earned=out.lifetime_earned,
            transaction_id=str(out.transaction_id),
        )
    return out


@router.post("/earn", response_model=TransactionResult)
async def internal_earn(
    body: InternalTransactionBody,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
) -> TransactionResult:
    payload = ProcessTransactionPayload(
        user_id=body.user_id,
        rule_code=body.rule_code,
        amount=body.amount,
        idempotency_key=body.idempotency_key,
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
            lifetime_earned=out.lifetime_earned,
            transaction_id=str(out.transaction_id),
        )
    return out
