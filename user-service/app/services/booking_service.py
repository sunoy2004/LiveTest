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


async def list_open_slots_for_connection(
    db: Session,
    *,
    user: User,
    connection_id: UUID,
) -> list[TimeSlot]:
    conn = db.query(MentorshipConnection).filter(MentorshipConnection.id == connection_id).first()
    if not conn:
         raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    mentor_id = conn.mentor_id

    return (
        db.query(TimeSlot)
        .filter(TimeSlot.mentor_id == mentor_id, TimeSlot.is_booked.is_(False), TimeSlot.pending_request_id.is_(None))
        .order_by(TimeSlot.start_time.asc())
        .all()
    )


async def mentee_booking_context(db: Session, *, user: User) -> dict | None:
    me = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not me:
        return None
    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.mentee_id == me.id, MentorshipConnection.status == "ACTIVE")
        .first()
    )
    if not conn:
        return None
    conn_id = conn.id
    mentor_id = conn.mentor_id
    cached_credits = me.cached_credit_score

    mentor = db.query(MentorProfile).filter(MentorProfile.id == mentor_id).first()
    m_user = db.query(User).filter(User.id == mentor.user_id).first() if mentor else None
    
    slots = (
        db.query(TimeSlot)
        .filter(TimeSlot.mentor_id == mentor_id, TimeSlot.is_booked.is_(False), TimeSlot.pending_request_id.is_(None))
        .all()
    )


    
    session_price = resolve_mentor_session_price(db, mentor) if mentor else 0
    
    return {
        "connection_id": conn_id,
        "mentor_display_name": m_user.email.split("@")[0].replace(".", " ").title() if m_user else "Mentor",
        "cached_credit_score": int(cached_credits),
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


async def book_slot_saga(
    db: Session,
    *,
    user: User,
    connection_id: UUID,
    slot_id: UUID,
    agreed_cost: int | None = None,
) -> dict:
    """Creates a pending session request (no credit movement until mentor accepts)."""
    log.info(
        "session booking request (scheduling path) connection_id=%s slot_id=%s",
        connection_id,
        slot_id,
    )
    return await create_session_booking_request(
        db,
        user=user,
        connection_id=connection_id,
        slot_id=slot_id,
        agreed_cost=agreed_cost,
    )
