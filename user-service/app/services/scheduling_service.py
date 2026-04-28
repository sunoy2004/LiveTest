from __future__ import annotations

import logging
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, MentorshipConnection, TimeSlot, User
from app.services.mentor_pricing import resolve_mentor_session_price
from app.services.session_booking_request_service import create_session_booking_request

log = logging.getLogger(__name__)


def _display_name_from_email(email: str | None) -> str:
    if not email:
        return "Mentor"
    local = email.split("@")[0]
    return local.replace(".", " ").replace("_", " ").title()


async def get_connected_mentors_for_mentee(db: Session, *, user: User) -> list[dict]:
    from app.services.mentoring_client import get_active_connections_from_mentoring_service
    remotes = await get_active_connections_from_mentoring_service(user.id)
    
    out: list[dict] = []
    for r in remotes:
        m_id = uuid.UUID(str(r["mentor_id"]))
        conn_id = uuid.UUID(str(r["id"]))
        
        mentor = db.query(MentorProfile).filter(MentorProfile.id == m_id).first()
        if not mentor:
            continue
        mentor_user = db.query(User).filter(User.id == mentor.user_id).first()
        if not mentor_user:
            continue
            
        cost = resolve_mentor_session_price(db, mentor)
        out.append(
            {
                "connection_id": conn_id,
                "mentor_id": m_id,
                "mentor_name": _display_name_from_email(mentor_user.email),
                "expertise": mentor.expertise_areas or [],
                "total_hours": mentor.total_hours_mentored,
                "tier": mentor.pricing_tier,
                "session_credit_cost": cost,
            }
        )
    return out


async def get_available_slots_for_mentor(
    db: Session,
    *,
    user: User,
    mentor_id: UUID,
) -> list[dict]:
    # Check connection remotely (Source of Truth)
    from app.services.mentoring_client import get_active_connections_from_mentoring_service
    remotes = await get_active_connections_from_mentoring_service(user.id)
    if not any(uuid.UUID(str(r["mentor_id"])) == mentor_id for r in remotes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not connected to this mentor")


    mentor = db.query(MentorProfile).filter(MentorProfile.id == mentor_id).first()
    if not mentor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentor not found")

    price = resolve_mentor_session_price(db, mentor)
    rows = (
        db.query(TimeSlot)
        .filter(
            TimeSlot.mentor_id == mentor_id,
            TimeSlot.is_booked.is_(False),
            TimeSlot.pending_request_id.is_(None),
        )
        .order_by(TimeSlot.start_time.asc())
        .all()
    )
    return [
        {
            "slot_id": r.id,
            "start_time": r.start_time,
            "end_time": r.end_time,
            "cost_credits": price,
        }
        for r in rows
    ]


async def book_session_simple(
    db: Session,
    *,
    user: User,
    connection_id: UUID,
    slot_id: UUID,
) -> dict:
    log.info(
        "session booking request (mentoring path) connection_id=%s slot_id=%s",
        connection_id,
        slot_id,
    )
    return await create_session_booking_request(
        db,
        user=user,
        connection_id=connection_id,
        slot_id=slot_id,
        agreed_cost=None,
    )
