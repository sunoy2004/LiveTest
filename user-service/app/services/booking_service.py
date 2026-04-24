"""Booking: slot availability + mentee scheduling context; booking creates a session request."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, MentorshipConnection, TimeSlot
from app.models import User
from app.services import credit_client
from app.services.mentor_pricing import resolve_mentor_session_price
from app.services.session_booking_request_service import create_session_booking_request

log = logging.getLogger(__name__)


def list_open_slots_for_connection(
    db: Session,
    *,
    user: User,
    connection_id: UUID,
) -> list[TimeSlot]:
    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.id == connection_id)
        .one_or_none()
    )
    if not conn or conn.status != "ACTIVE":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    mp = db.query(MentorProfile).filter(MentorProfile.id == conn.mentor_id).one()
    me = db.query(MenteeProfile).filter(MenteeProfile.id == conn.mentee_id).one()
    if user.id not in (mp.user_id, me.user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this connection")
    return (
        db.query(TimeSlot)
        .filter(
            TimeSlot.mentor_id == conn.mentor_id,
            TimeSlot.is_booked.is_(False),
            TimeSlot.pending_request_id.is_(None),
        )
        .order_by(TimeSlot.start_time.asc())
        .all()
    )


def mentee_booking_context(db: Session, *, user: User) -> dict | None:
    """First ACTIVE connection for this user's mentee profile + open slots.

    Note: we pick a deterministic connection (mentor email ASC) so the mentee UI
    consistently shows a mentor name + slots when multiple connections exist.
    """
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        return None
    conn = (
        db.query(MentorshipConnection)
        .join(MentorProfile, MentorProfile.id == MentorshipConnection.mentor_id)
        .join(User, User.id == MentorProfile.user_id)
        .filter(
            MentorshipConnection.mentee_id == mentee.id,
            MentorshipConnection.status == "ACTIVE",
        )
        .order_by(User.email.asc(), MentorshipConnection.id.asc())
        .first()
    )
    if not conn:
        return None
    slots = list_open_slots_for_connection(db, user=user, connection_id=conn.id)
    mentor = db.query(MentorProfile).filter(MentorProfile.id == conn.mentor_id).one()
    mentor_user = db.query(User).filter(User.id == mentor.user_id).one()
    session_price = resolve_mentor_session_price(db, mentor)
    bal_json = credit_client.get_balance(mentee.user_id)
    display_credits = int(mentee.cached_credit_score)
    if bal_json is not None and bal_json.get("balance") is not None:
        display_credits = int(bal_json["balance"])
    return {
        "connection_id": conn.id,
        "mentor_display_name": mentor_user.email.split("@")[0].replace(".", " ").title(),
        "cached_credit_score": display_credits,
        "slots": [
            {
                "id": s.id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "cost_credits": session_price,
            }
            for s in slots
        ],
    }


def book_slot_saga(
    db: Session,
    *,
    user: User,
    connection_id: UUID,
    slot_id: UUID,
    agreed_cost: int,
) -> dict:
    """Creates a pending session request (no credit movement until mentor accepts)."""
    log.info(
        "session booking request (scheduling path) connection_id=%s slot_id=%s agreed_cost=%s",
        connection_id,
        slot_id,
        agreed_cost,
    )
    return create_session_booking_request(
        db,
        user=user,
        connection_id=connection_id,
        slot_id=slot_id,
        agreed_cost=agreed_cost,
    )
