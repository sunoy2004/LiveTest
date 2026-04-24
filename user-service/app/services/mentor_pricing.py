"""Resolve per-session credit price: admin override, else gamification BOOK_MENTOR_SESSION base."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import MentorProfile
from app.services import credit_client


def resolve_mentor_session_price(db: Session, mentor: MentorProfile) -> int:
    """
    If base_credit_override is set → use it (admin special price for that mentor).
    Else → gamification activity rule BOOK_MENTOR_SESSION.base_credit_value
    (same amount used when deducting via internal /transactions/deduct).
    """
    _ = db  # kept for call-site compatibility
    if mentor.base_credit_override is not None:
        return max(1, int(mentor.base_credit_override))

    base = credit_client.get_book_mentor_session_base_credits()
    return max(1, int(base))
