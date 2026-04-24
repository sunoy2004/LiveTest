from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.gamification.models import ActivityRule, LedgerTransaction, TransactionType, Wallet
from app.services.gamification.schemas.payloads import ProcessTransactionPayload, TransactionResult
from app.services.gamification.utils.integrity import verify_wallet_integrity
from app.services.gamification.services.exceptions import (
    CooldownActiveError,
    InsufficientFundsError,
    InvalidAmountError,
    RuleInactiveError,
    RuleNotFoundError,
)


async def process_transaction(
    session: AsyncSession,
    payload: ProcessTransactionPayload,
) -> TransactionResult:
    rule_res = await session.execute(
        select(ActivityRule).where(ActivityRule.rule_code == payload.rule_code)
    )
    rule = rule_res.scalar_one_or_none()
    if not rule:
        raise RuleNotFoundError(payload.rule_code)
    if not rule.is_active:
        raise RuleInactiveError(payload.rule_code)

    raw_amount = payload.amount if payload.amount is not None else rule.base_credit_value
    if raw_amount < 1:
        raise InvalidAmountError("credit amount must be at least 1")

    ttype = TransactionType(rule.transaction_type)
    if ttype == TransactionType.SPEND:
        signed_delta = -raw_amount
    else:
        signed_delta = raw_amount

    if rule.cooldown_seconds > 0:
        cool_res = await session.execute(
            select(LedgerTransaction.created_at)
            .where(
                LedgerTransaction.user_id == payload.user_id,
                LedgerTransaction.rule_code == payload.rule_code,
            )
            .order_by(desc(LedgerTransaction.created_at))
            .limit(1)
        )
        last_ts = cool_res.scalar_one_or_none()
        if last_ts:
            elapsed = (datetime.now(timezone.utc) - last_ts).total_seconds()
            if elapsed < rule.cooldown_seconds:
                raise CooldownActiveError()

    w = await _lock_wallet(session, payload.user_id)
    new_balance = w.current_balance + signed_delta
    if new_balance < 0:
        raise InsufficientFundsError()

    now = datetime.now(timezone.utc)
    lt = LedgerTransaction(
        user_id=payload.user_id,
        rule_code=payload.rule_code,
        amount=signed_delta,
        balance_after=new_balance,
        idempotency_key=payload.idempotency_key,
        created_at=now,
    )
    session.add(lt)
    try:
        await session.flush()
    except IntegrityError:
        # Idempotency race: another worker inserted the same key first.
        await session.rollback()
        existing = await session.execute(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == payload.idempotency_key)
        )
        row = existing.scalar_one()
        # Re-lock wallet for consistent read.
        w2 = await _lock_wallet(session, row.user_id)
        return TransactionResult(
            transaction_id=row.transaction_id,
            user_id=row.user_id,
            rule_code=row.rule_code,
            amount=row.amount,
            balance_after=row.balance_after,
            lifetime_earned=w2.lifetime_earned,
            idempotent_replay=True,
        )

    w.current_balance = new_balance
    if signed_delta > 0:
        w.lifetime_earned += signed_delta
    w.last_updated_at = now

    await session.flush()
    await verify_wallet_integrity(session, payload.user_id)

    return TransactionResult(
        transaction_id=lt.transaction_id,
        user_id=payload.user_id,
        rule_code=payload.rule_code,
        amount=signed_delta,
        balance_after=new_balance,
        lifetime_earned=w.lifetime_earned,
        idempotent_replay=False,
    )


async def _lock_wallet(session: AsyncSession, user_id: UUID) -> Wallet:
    res = await session.execute(
        select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    )
    w = res.scalar_one_or_none()
    if w is None:
        now = datetime.now(timezone.utc)
        w = Wallet(user_id=user_id, current_balance=0, lifetime_earned=0, last_updated_at=now)
        session.add(w)
        await session.flush()
        res = await session.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        )
        w = res.scalar_one()
    return w
