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
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentee profile not found")

    # --- CROSS-SERVICE BRIDGE ---
    from app.services.mentoring_client import get_active_connections_from_mentoring_service
    remote_conns = await get_active_connections_from_mentoring_service(user.id)
    if remote_conns:
        out: list[dict] = []
        for c in remote_conns:
            # We need to fetch mentor details from local DB to get expertise/tier
            mentor_id = UUID(str(c["mentor_id"]))
            mentor = db.query(MentorProfile).filter(MentorProfile.id == mentor_id).first()
            if not mentor:
                continue
            mentor_user = db.query(User).filter(User.id == mentor.user_id).first()
            cost = resolve_mentor_session_price(db, mentor)
            out.append({
                "connection_id": UUID(str(c["id"])),
                "mentor_id": mentor.id,
                "mentor_name": c.get("mentor_name") or _display_name_from_email(mentor_user.email if mentor_user else ""),
                "expertise": mentor.expertise_areas or [],
                "total_hours": mentor.total_hours_mentored,
                "tier": mentor.pricing_tier,
                "session_credit_cost": cost,
            })
        return out
    # --- END BRIDGE ---
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentee profile not found")

    q = (
        db.query(MentorshipConnection, MentorProfile, User)
        .join(MentorProfile, MentorProfile.id == MentorshipConnection.mentor_id)
        .join(User, User.id == MentorProfile.user_id)
        .filter(
            MentorshipConnection.mentee_id == mentee.id,
            MentorshipConnection.status == "ACTIVE",
        )
        .order_by(User.email.asc())
    )

    out: list[dict] = []
    for conn, mentor, mentor_user in q.all():
        cost = resolve_mentor_session_price(db, mentor)
        out.append(
            {
                "connection_id": conn.id,
                "mentor_id": mentor.id,
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
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentee profile not found")

    # --- CROSS-SERVICE BRIDGE ---
    from app.services.mentoring_client import get_active_connections_from_mentoring_service
    remote_conns = await get_active_connections_from_mentoring_service(user.id)
    is_connected = any(UUID(str(c["mentor_id"])) == mentor_id for c in remote_conns)
    
    if not is_connected:
        # Fallback to local
        conn = (
            db.query(MentorshipConnection)
            .filter(
                MentorshipConnection.mentee_id == mentee.id,
                MentorshipConnection.mentor_id == mentor_id,
                MentorshipConnection.status == "ACTIVE",
            )
            .first()
        )
        if not conn:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not connected to this mentor")
    # --- END BRIDGE ---

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
