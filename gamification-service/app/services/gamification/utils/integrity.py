from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.gamification.models import LedgerTransaction, Wallet

log = logging.getLogger(__name__)


async def verify_wallet_integrity(session: AsyncSession, user_id: UUID) -> bool:
    """
    Verifies wallet snapshot matches ledger sum.
    Returns True if consistent; logs mismatch and returns False otherwise.
    """
    sum_res = await session.execute(
        select(func.coalesce(func.sum(LedgerTransaction.amount), 0)).where(LedgerTransaction.user_id == user_id)
    )
    ledger_sum = int(sum_res.scalar_one())
    w_res = await session.execute(select(Wallet).where(Wallet.user_id == user_id))
    w = w_res.scalar_one_or_none()
    wallet_bal = int(w.current_balance) if w else 0
    if ledger_sum != wallet_bal:
        log.error(
            "wallet integrity mismatch user_id=%s wallet=%s ledger_sum=%s",
            user_id,
            wallet_bal,
            ledger_sum,
        )
        return False
    return True

