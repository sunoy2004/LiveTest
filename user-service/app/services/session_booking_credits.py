"""Credit deduction for mentoring session booking (gamification-service ledger)."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import CreditLedgerEntry, MenteeProfile
from app.services import credit_client

log = logging.getLogger(__name__)


def resolve_new_balance_for_booking(
    *,
    mentee_profile: MenteeProfile,
    mentee_user_id: UUID,
    session_cost: int,
    idempotency_key: str | None = None,
) -> tuple[int, bool]:
    """
    Returns (balance after booking, True when gamification ledger applied the deduct).

    Raises HTTP 402 when credits are insufficient; 503 when gamification is not configured.
    """
    if session_cost <= 0:
        return int(mentee_profile.cached_credit_score), False

    if not credit_client.GAMIFICATION_SERVICE_URL:
        log.error("booking blocked: GAMIFICATION_SERVICE_URL not set")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gamification service is required for booking",
        )
    if not credit_client.INTERNAL_API_TOKEN:
        log.error("booking blocked: INTERNAL_API_TOKEN not set")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gamification internal API is not configured",
        )
    if not idempotency_key:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Booking idempotency key missing",
        )

    log.info(
        "booking deduct: mentee_user_id=%s amount=%s idempotency_key=%s",
        mentee_user_id,
        session_cost,
        idempotency_key,
    )
    ok, new_bal = credit_client.deduct_booking(
        user_id=mentee_user_id,
        amount=session_cost,
        idempotency_key=idempotency_key,
    )
    if not ok or new_bal is None:
        log.warning(
            "booking deduct failed or insufficient funds mentee_user_id=%s amount=%s",
            mentee_user_id,
            session_cost,
        )
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Insufficient credits",
        )
    log.info(
        "booking deduct ok: mentee_user_id=%s balance_after=%s",
        mentee_user_id,
        new_bal,
    )
    return new_bal, True


def refund_session_booking_credits(
    mentee_user_id: UUID,
    session_cost: int,
    *,
    used_remote_credit_service: bool,
) -> None:
    if session_cost <= 0 or not used_remote_credit_service:
        return
    credit_client.add_credits(mentee_user_id, session_cost)


def append_booking_ledger(
    db: Session,
    *,
    mentee_user_id: UUID,
    session_cost: int,
    new_balance: int,
    session_id: UUID,
) -> None:
    if session_cost <= 0:
        return
    db.add(
        CreditLedgerEntry(
            user_id=mentee_user_id,
            delta=-session_cost,
            balance_after=new_balance,
            reason=f"Mentoring session scheduled ({session_id})",
        )
    )
