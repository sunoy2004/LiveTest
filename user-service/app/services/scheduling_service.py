from __future__ import annotations

import logging
import os
import uuid
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, TimeSlot, User
from app.services.mentor_pricing import resolve_mentor_session_price
from app.services.session_booking_request_service import create_session_booking_request

log = logging.getLogger(__name__)

MENTORING_SERVICE_URL = os.getenv(
    "MENTORING_SERVICE_URL", 
    "https://mentoring-service-1095720168864-1095720168864.us-central1.run.app"
)


async def _fetch_connections_from_service(user_id: uuid.UUID) -> list[dict]:
    """Call Mentoring Service to get active connections for a user."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{MENTORING_SERVICE_URL}/api/v1/requests/connections",
                headers={"X-User-Id": str(user_id)}
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return []


def _display_name_from_email(email: str | None) -> str:
    if not email:
        return "Mentor"
    local = email.split("@")[0]
    return local.replace(".", " ").replace("_", " ").title()


async def get_connected_mentors_for_mentee(db: Session, *, user: User) -> list[dict]:
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentee profile not found")

    conns = await _fetch_connections_from_service(user.id)
    out: list[dict] = []
    
    for conn in conns:
        # The Mentoring Service returns connections where the user is either mentor or mentee.
        # We only care about connections where the current user is the MENTEE.
        if str(conn["mentee_id"]) != str(mentee.id):
            continue
            
        mentor_profile_id = UUID(str(conn["mentor_id"]))
        row = (
            db.query(MentorProfile, User)
            .join(User, User.id == MentorProfile.user_id)
            .filter(MentorProfile.id == mentor_profile_id)
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
    *,
    user: User,
    mentor_id: UUID,
) -> list[dict]:
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentee profile not found")

    conns = await _fetch_connections_from_service(user.id)
    conn = next((c for c in conns if str(c["mentor_id"]) == str(mentor_id) and str(c["mentee_id"]) == str(mentee.id)), None)
    
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
