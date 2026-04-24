from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.services.gamification.models import LedgerTransaction, Wallet
from app.services.gamification.schemas.payloads import LedgerItem, WalletPublic

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/me", response_model=WalletPublic)
async def wallet_me(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> WalletPublic:
    res = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    w = res.scalar_one_or_none()
    if not w:
        return WalletPublic(user_id=user_id, current_balance=0, lifetime_earned=0)
    return WalletPublic(
        user_id=w.user_id,
        current_balance=w.current_balance,
        lifetime_earned=w.lifetime_earned,
    )


@router.get("/history", response_model=list[LedgerItem])
async def wallet_history(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[LedgerItem]:
    res = await db.execute(
        select(LedgerTransaction)
        .where(LedgerTransaction.user_id == user_id)
        .order_by(desc(LedgerTransaction.created_at))
        .offset(offset)
        .limit(limit)
    )
    rows = res.scalars().all()
    return [
        LedgerItem(
            transaction_id=r.transaction_id,
            rule_code=r.rule_code,
            amount=r.amount,
            balance_after=r.balance_after,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]
