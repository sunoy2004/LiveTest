from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import os

from app.db.session import get_db
from app.deps import require_admin_session
from app.services.gamification.constants import ADMIN_DEDUCT, ADMIN_GRANT
from app.services.gamification.events.publisher import publish_credit_score_updated
from app.services.gamification.models import ActivityRule, LedgerTransaction, Wallet
from app.services.gamification.schemas.admin import ActivityRuleOut, AdminWalletBody, RuleUpdateBody
from app.services.gamification.schemas.payloads import ProcessTransactionPayload, TransactionResult
from app.services.gamification.api.errors import raise_http
from app.services.gamification.services.exceptions import GamificationError
from app.services.gamification.services.ledger_engine import process_transaction

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/rules", response_model=list[ActivityRuleOut])
async def list_rules(
    _: None = Depends(require_admin_session),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityRuleOut]:
    res = await db.execute(select(ActivityRule).order_by(ActivityRule.rule_code.asc()))
    rows = res.scalars().all()
    return [
        ActivityRuleOut(
            rule_code=r.rule_code,
            transaction_type=r.transaction_type,
            base_credit_value=r.base_credit_value,
            is_active=r.is_active,
            cooldown_seconds=r.cooldown_seconds,
        )
        for r in rows
    ]


# Static GET paths before /wallet/{user_id}/... so routing stays unambiguous across ASGI stacks.
@router.get("/wallets")
async def list_wallets(
    _: None = Depends(require_admin_session),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> dict:
    """All wallets: user id, current balance, and lifetime earned (for admin overview)."""
    cq = select(func.count()).select_from(Wallet)
    total = (await db.execute(cq)).scalar_one()
    offset = (page - 1) * page_size
    q = (
        select(Wallet)
        .order_by(Wallet.lifetime_earned.desc(), Wallet.user_id.asc())
        .offset(offset)
        .limit(page_size)
    )
    res = await db.execute(q)
    rows = res.scalars().all()
    
    names = {}
    try:
        internal_token = os.getenv("INTERNAL_API_TOKEN", "")
        user_svc = os.getenv("USER_SERVICE_URL", "https://user-service-1095720168864-1095720168864.us-central1.run.app")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{user_svc}/internal/users/names",
                headers={"X-Internal-Token": internal_token},
                timeout=2.0
            )
            if resp.status_code == 200:
                names = resp.json()
    except Exception:
        pass

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "user_id": str(w.user_id),
                "user_name": names.get(str(w.user_id), "Unknown User"),
                "current_balance": w.current_balance,
                "lifetime_earned": w.lifetime_earned,
            }
            for w in rows
        ],
    }



@router.get("/ledger")
async def admin_ledger(
    _: None = Depends(require_admin_session),
    db: AsyncSession = Depends(get_db),
    user_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> dict:
    cq = select(func.count()).select_from(LedgerTransaction)
    if user_id is not None:
        cq = cq.where(LedgerTransaction.user_id == user_id)
    total = (await db.execute(cq)).scalar_one()
    q = select(LedgerTransaction)
    if user_id is not None:
        q = q.where(LedgerTransaction.user_id == user_id)
    offset = (page - 1) * page_size
    q = q.order_by(desc(LedgerTransaction.created_at)).offset(offset).limit(page_size)
    res = await db.execute(q)
    rows = res.scalars().all()
    
    names = {}
    try:
        internal_token = os.getenv("INTERNAL_API_TOKEN", "")
        user_svc = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{user_svc}/internal/users/names",
                headers={"X-Internal-Token": internal_token},
                timeout=2.0
            )
            if resp.status_code == 200:
                names = resp.json()
    except Exception:
        pass

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "transaction_id": str(r.transaction_id),
                "user_id": str(r.user_id),
                "user_name": names.get(str(r.user_id), "Unknown User"),
                "rule_code": r.rule_code,
                "amount": r.amount,
                "balance_after": r.balance_after,
                "idempotency_key": r.idempotency_key,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.put("/rules/{rule_code}", response_model=ActivityRuleOut)
async def update_rule(
    rule_code: str,
    body: RuleUpdateBody,
    _: None = Depends(require_admin_session),
    db: AsyncSession = Depends(get_db),
) -> ActivityRuleOut:
    res = await db.execute(select(ActivityRule).where(ActivityRule.rule_code == rule_code))
    rule = res.scalar_one_or_none()
    if not rule:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    if body.base_credit_value is not None:
        rule.base_credit_value = body.base_credit_value
    if body.is_active is not None:
        rule.is_active = body.is_active
    if body.cooldown_seconds is not None:
        rule.cooldown_seconds = body.cooldown_seconds
    rule.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return ActivityRuleOut(
        rule_code=rule.rule_code,
        transaction_type=rule.transaction_type,
        base_credit_value=rule.base_credit_value,
        is_active=rule.is_active,
        cooldown_seconds=rule.cooldown_seconds,
    )


@router.post("/wallet/{user_id}/grant", response_model=TransactionResult)
async def admin_grant(
    user_id: UUID,
    body: AdminWalletBody,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_admin_session),
    db: AsyncSession = Depends(get_db),
) -> TransactionResult:
    payload = ProcessTransactionPayload(
        user_id=user_id,
        rule_code=ADMIN_GRANT,
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
            transaction_id=str(out.transaction_id),
        )
    return out


@router.post("/wallet/{user_id}/deduct", response_model=TransactionResult)
async def admin_deduct(
    user_id: UUID,
    body: AdminWalletBody,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_admin_session),
    db: AsyncSession = Depends(get_db),
) -> TransactionResult:
    payload = ProcessTransactionPayload(
        user_id=user_id,
        rule_code=ADMIN_DEDUCT,
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
            transaction_id=str(out.transaction_id),
        )
    return out
