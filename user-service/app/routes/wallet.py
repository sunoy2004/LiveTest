from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import CreditLedgerEntry, User
from app.schemas import CreditLedgerItem

router = APIRouter(tags=["wallet"])


@router.get("/wallet/transactions", response_model=list[CreditLedgerItem])
def list_wallet_transactions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
):
    rows = (
        db.query(CreditLedgerEntry)
        .filter(CreditLedgerEntry.user_id == user.id)
        .order_by(CreditLedgerEntry.created_at.desc())
        .limit(limit)
        .all()
    )
    return [CreditLedgerItem.model_validate(r) for r in rows]
