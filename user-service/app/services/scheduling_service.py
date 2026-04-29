from __future__ import annotations
import logging
import uuid
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import MenteeProfile, MentorProfile, MentorshipConnection, TimeSlot, User
from app.services.mentor_pricing import resolve_mentor_session_price
from app.services.session_booking_request_service import create_session_booking_request

log = logging.getLogger(__name__)


def _fetch_connections_from_db(mentoring_db: Session, user_id: uuid.UUID) -> list[dict]:
    """Directly query Mentoring DB for active connections for a user."""
    # First find the profile IDs in the mentoring DB
    mentor = mentoring_db.query(MentorProfile).filter(MentorProfile.user_id == user_id).first()
    mentee = mentoring_db.query(MenteeProfile).filter(MenteeProfile.user_id == user_id).first()
    
    mentor_id = mentor.id if mentor else None
    mentee_id = mentee.id if mentee else None
    
    if not mentor_id and not mentee_id:
        return []

    q = (
        mentoring_db.query(MentorshipConnection, MentorProfile.user_id.label("m_uid"), MenteeProfile.user_id.label("me_uid"))
        .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
        .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
        .filter(
            or_(
                MentorshipConnection.mentor_id == mentor_id,
                MentorshipConnection.mentee_id == mentee_id
            ),
            MentorshipConnection.status == "ACTIVE"
        )
    )
    
    out = []
    for conn, m_uid, me_uid in q.all():
        out.append({
            "id": str(conn.id),
            "mentee_id": str(conn.mentee_id),
            "mentor_id": str(conn.mentor_id),
            "mentee_user_id": str(me_uid),
            "mentor_user_id": str(m_uid),
            "status": "ACTIVE"
        })
    return out


def _display_name_from_email(email: str | None) -> str:
    if not email:
        return "Mentor"
    local = email.split("@")[0]
    return local.replace(".", " ").replace("_", " ").title()


async def get_connected_mentors_for_mentee(db: Session, mentoring_db: Session, *, user: User) -> list[dict]:
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentee profile not found")

    conns = _fetch_connections_from_db(mentoring_db, user.id)
    out: list[dict] = []
    
    for conn in conns:
        # We use mentor_user_id/mentee_user_id for reliable mapping across services.
        if str(conn["mentee_user_id"]) != str(user.id):
            continue
            
        mentor_user_id = UUID(str(conn["mentor_user_id"]))
        row = (
            db.query(MentorProfile, User)
            .join(User, User.id == MentorProfile.user_id)
            .filter(User.id == mentor_user_id)
            .first()
        )
        if not row:
            continue
            
        mentor, mentor_user = row
        cost = resolve_mentor_session_price(db, mentor)
        out.append(
            {
                "connection_id": UUID(str(conn["id"])),
                "mentor_id": mentor.id,
                "mentor_name": _display_name_from_email(mentor_user.email),
                "expertise": mentor.expertise_areas or [],
                "total_hours": mentor.total_hours_mentored,
                "tier": mentor.pricing_tier,
                "session_credit_cost": cost,
            }
        )
    return sorted(out, key=lambda x: x["mentor_name"])


async def get_available_slots_for_mentor(
    db: Session,
    mentoring_db: Session,
    *,
    user: User,
    mentor_id: UUID,
) -> list[dict]:
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentee profile not found")

    conns = _fetch_connections_from_db(mentoring_db, user.id)
    conn = None
    for c in conns:
        # Check if connected (mentor_id here is User Profile ID from User DB)
        # We need to map it back to user_id to check against conn["mentor_user_id"]
        mentor_p = db.query(MentorProfile).filter(MentorProfile.id == mentor_id).first()
        if not mentor_p:
            continue
        if str(c["mentee_user_id"]) == str(user.id) and str(c["mentor_user_id"]) == str(mentor_p.user_id):
            conn = c
            break
    
    if not conn:
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
