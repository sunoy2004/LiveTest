"""Mentee credit balance (cached_credit_score) — saga helpers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import MenteeProfile


def deduct_credits_for_mentee(
    db: Session,
    *,
    mentee_profile_id: UUID,
    amount: int,
) -> int | None:
    """
    Deduct credits on an already row-locked MenteeProfile row (caller must hold FOR UPDATE).
    Returns new balance, or None if insufficient (caller should not proceed).
    """
    row = db.get(MenteeProfile, mentee_profile_id)
    if row is None:
        return None
    if row.cached_credit_score < amount:
        return None
    row.cached_credit_score -= amount
    return row.cached_credit_score
