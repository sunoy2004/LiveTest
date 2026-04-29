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


async def ensure_connection_synced(db: Session, *, user: User, connection_id: UUID) -> MentorshipConnection:
    """
    Ensure the MentorshipConnection exists in users_db with the same ID as mentoring_db.
    Maps user_ids from Mentoring Service to local Profile IDs.
    """
    from app.models import MentorshipConnection
    
    # 1. Check local
    conn = db.query(MentorshipConnection).filter(MentorshipConnection.id == connection_id).first()
    if conn:
        return conn
        
    # 2. Fetch all connections for this user from Mentoring Service
    conns = await _fetch_connections_from_service(user.id)
    match = next((c for c in conns if str(c["id"]) == str(connection_id)), None)
    
    if not match:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, 
            f"Connection {connection_id} not found for user {user.id} in Mentoring Service"
        )
        
    # 3. Create local stub mapping User IDs to local Profile IDs
    mentor_user_id = UUID(str(match["mentor_user_id"]))
    mentee_user_id = UUID(str(match["mentee_user_id"]))
    
    mentor_p = db.query(MentorProfile).filter(MentorProfile.user_id == mentor_user_id).first()
    mentee_p = db.query(MenteeProfile).filter(MenteeProfile.user_id == mentee_user_id).first()
    
    if not mentor_p or not mentee_p:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, 
            "Required profiles (mentor/mentee) missing in User Service for this connection"
        )
        
    stub = MentorshipConnection(
        id=connection_id,
        mentor_id=mentor_p.id,
        mentee_id=mentee_p.id,
        status="ACTIVE"
    )
    db.add(stub)
    db.commit()
    db.refresh(stub)
    return stub


async def get_connected_mentors_for_mentee(db: Session, *, user: User) -> list[dict]:
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentee profile not found")

    conns = await _fetch_connections_from_service(user.id)
    out: list[dict] = []
    
    for conn in conns:
        # The Mentoring Service returns connections where the user is either mentor or mentee.
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
    *,
    user: User,
    mentor_id: UUID,
) -> list[dict]:
    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not mentee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentee profile not found")

    # This will throw 404 if not found or 403-ish if the user isn't part of it
    conns = await _fetch_connections_from_service(user.id)
    conn_data = next((c for c in conns if str(c["mentor_user_id"]) == str(mentor_id)), None)
    
    if not conn_data:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not connected to this mentor")

    # Sync it locally so we can create booking requests against it
    await ensure_connection_synced(db, user=user, connection_id=UUID(str(conn_data["id"])))



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
    # Ensure the connection exists locally before creating the booking request
    await ensure_connection_synced(db, user=user, connection_id=connection_id)
    
    return await create_session_booking_request(
        db,
        user=user,
        connection_id=connection_id,
        slot_id=slot_id,
        agreed_cost=None,
    )


async def get_my_availability(db: Session, *, user: User) -> list[dict]:
    mentor = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
    if not mentor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentor profile not found")

    rows = (
        db.query(TimeSlot)
        .filter(TimeSlot.mentor_id == mentor.id)
        .order_by(TimeSlot.start_time.asc())
        .all()
    )
    return [
        {
            "slot_id": r.id,
            "start_time": r.start_time,
            "end_time": r.end_time,
            "is_booked": r.is_booked,
            "pending_request_id": r.pending_request_id,
        }
        for r in rows
    ]


async def add_availability(
    db: Session,
    *,
    user: User,
    start_time: datetime,
    end_time: datetime,
) -> dict:
    mentor = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
    if not mentor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentor profile not found")

    slot = TimeSlot(
        mentor_id=mentor.id,
        start_time=start_time,
        end_time=end_time,
        is_booked=False,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return {"slot_id": slot.id, "status": "created"}


async def delete_availability(db: Session, *, user: User, slot_id: UUID) -> dict:
    mentor = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
    if not mentor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentor profile not found")

    slot = (
        db.query(TimeSlot)
        .filter(TimeSlot.id == slot_id, TimeSlot.mentor_id == mentor.id)
        .first()
    )
    if not slot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")

    if slot.is_booked or slot.pending_request_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot delete a booked or pending slot"
        )

    db.delete(slot)
    db.commit()
    return {"status": "deleted"}
