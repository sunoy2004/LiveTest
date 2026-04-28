"""Session booking: mentee requests slot → mentor accepts (deduct + session) or rejects."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, MentorshipConnection, SessionBookingRequest, TimeSlot, User
from app.models import Session as MentorshipSession
from app.services import event_bus
from app.services.google_meet_service import resolve_session_meeting_url
from app.services.mentor_pricing import resolve_mentor_session_price
from app.services.session_booking_credits import (
    append_booking_ledger,
    refund_session_booking_credits,
    resolve_new_balance_for_booking,
)

log = logging.getLogger(__name__)


def _party_user_ids(db: Session, conn: MentorshipConnection) -> tuple[UUID, UUID]:
    mp = db.query(MentorProfile).filter(MentorProfile.id == conn.mentor_id).one()
    me = db.query(MenteeProfile).filter(MenteeProfile.id == conn.mentee_id).one()
    return mp.user_id, me.user_id


async def create_session_booking_request(
    db: Session,
    *,
    user: User,
    connection_id: UUID,
    slot_id: UUID,
    agreed_cost: int | None,
) -> dict:
    """
    Hold slot (no credit movement). Notifies mentor via mentoring.connections.events.
    agreed_cost: when set (scheduling path), must match resolved mentor session price.
    """
    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.id == connection_id)
        .one_or_none()
    )
    # --- CROSS-SERVICE BRIDGE: Auto-Sync ---
    if not conn:
        from app.services.mentoring_client import get_active_connections_from_mentoring_service
        remotes = await get_active_connections_from_mentoring_service(user.id)
        # Check if requested connection_id exists in remote active list
        remote_match = next((r for r in remotes if UUID(str(r["id"])) == connection_id), None)
        if not remote_match:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found locally or in Mentoring Service")
        
        # Create local shadow copy for FK consistency
        conn = MentorshipConnection(
            id=connection_id,
            mentor_id=UUID(str(remote_match["mentor_id"])),
            mentee_id=UUID(str(remote_match["mentee_id"])),
            status="ACTIVE"
        )
        db.add(conn)
        db.flush() # flush so it's available for queries below
        log.info("Auto-synced connection %s from Mentoring Service", connection_id)

    if conn.status != "ACTIVE":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection is inactive")

    mentor_id = conn.mentor_id
    mentee_id = conn.mentee_id

    mentee_profile = (
        db.query(MenteeProfile)
        .filter(MenteeProfile.id == mentee_id)
        .one_or_none()
    )
    if not mentee_profile or mentee_profile.user_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only the mentee on this connection can request a session",
        )

    mentor = db.query(MentorProfile).filter(MentorProfile.id == mentor_id).one()
    session_cost = resolve_mentor_session_price(db, mentor)
    if agreed_cost is not None and agreed_cost != session_cost:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "agreed_cost must match the resolved session price (admin override or BOOK_MENTOR_SESSION base)",
        )

    slot = (
        db.query(TimeSlot)
        .filter(TimeSlot.id == slot_id)
        .with_for_update()
        .one_or_none()
    )
    if not slot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")
    if slot.mentor_id != mentor_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Slot does not belong to this connection's mentor",
        )
    if slot.is_booked:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot already booked")
    if slot.pending_request_id is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This slot already has a pending session request",
        )

    dup = (
        db.query(SessionBookingRequest)
        .filter(
            SessionBookingRequest.slot_id == slot_id,
            SessionBookingRequest.status == "PENDING",
        )
        .first()
    )
    if dup is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This slot already has a pending session request",
        )

    req = SessionBookingRequest(
        connection_id=connection_id,
        slot_id=slot.id,
        status="PENDING",
        agreed_cost=session_cost,
    )
    db.add(req)
    db.flush()
    slot.pending_request_id = req.id
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(req)

    mentor_uid, mentee_uid = _party_user_ids(db, conn)
    event_bus.publish_connections_event(
        event_bus.TOPIC_SESSION_BOOKING_REQUESTED,
        {
            "request_id": str(req.id),
            "connection_id": str(conn.id),
            "slot_id": str(slot.id),
            "start_time": slot.start_time.isoformat(),
            "agreed_cost": session_cost,
            "mentor_user_id": str(mentor_uid),
            "mentee_user_id": str(mentee_uid),
        },
        notify_user_ids=[mentor_uid],
    )

    return {
        "request_id": req.id,
        "status": "PENDING_APPROVAL",
        "session_id": None,
        "meeting_url": None,
        "start_time": slot.start_time,
    }


async def accept_session_booking_request(
    db: Session,
    *,
    user: User,
    request_id: UUID,
) -> MentorshipSession:
    req = (
        db.query(SessionBookingRequest)
        .filter(SessionBookingRequest.id == request_id)
        .with_for_update()
        .one_or_none()
    )
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if req.status != "PENDING":
        raise HTTPException(status.HTTP_409_CONFLICT, "Request is no longer pending")

    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.id == req.connection_id)
        .one_or_none()
    )
    if not conn:
        # Fallback for old requests or edge cases
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Active connection not found for this request")
    
    mentor_id = conn.mentor_id
    mentee_id = conn.mentee_id

    mentor = db.query(MentorProfile).filter(MentorProfile.id == mentor_id).one()
    if mentor.user_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only the mentor can accept this request",
        )

    mentee_profile = (
        db.query(MenteeProfile)
        .filter(MenteeProfile.id == mentee_id)
        .one()
    )
    slot = (
        db.query(TimeSlot)
        .filter(TimeSlot.id == req.slot_id)
        .with_for_update()
        .one_or_none()
    )
    if not slot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")
    if slot.pending_request_id != req.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Slot is no longer held for this request",
        )
    if slot.is_booked:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot already booked")

    session_cost = int(req.agreed_cost)
    mentor_uid, mentee_uid = _party_user_ids(db, conn)

    used_remote = False
    try:
        slot.is_booked = True
        slot.pending_request_id = None

        session_row = MentorshipSession(
            connection_id=conn.id,
            slot_id=slot.id,
            start_time=slot.start_time,
            status="SCHEDULED",
            meeting_url=None,
            mentor_id=conn.mentor_id,
            mentee_id=conn.mentee_id,
            price_charged=session_cost,
        )
        db.add(session_row)
        db.flush()

        new_balance, used_remote = resolve_new_balance_for_booking(
            mentee_profile=mentee_profile,
            mentee_user_id=mentee_uid,
            session_cost=session_cost,
            idempotency_key=str(session_row.id),
        )
        mentor_user_row = db.query(User).filter(User.id == mentor_uid).first()
        mentee_user_row = db.query(User).filter(User.id == mentee_uid).first()
        session_row.meeting_url = resolve_session_meeting_url(
            session_id=session_row.id,
            fallback_url=f"https://meet.example.com/s-{uuid.uuid4().hex[:10]}",
            slot_start=slot.start_time,
            slot_end=slot.end_time,
            mentor_email=mentor_user_row.email if mentor_user_row else None,
            mentee_email=mentee_user_row.email if mentee_user_row else None,
        )
        mentee_profile.cached_credit_score = new_balance
        append_booking_ledger(
            db,
            mentee_user_id=mentee_uid,
            session_cost=session_cost,
            new_balance=new_balance,
            session_id=session_row.id,
        )

        req.status = "ACCEPTED"
        req.session_id = session_row.id
        req.resolved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(session_row)
        db.refresh(mentee_profile)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        refund_session_booking_credits(
            mentee_uid,
            session_cost,
            used_remote_credit_service=used_remote,
        )
        raise

    event_bus.publish_event(
        event_bus.TOPIC_SESSION_SCHEDULED,
        {
            "session_id": str(session_row.id),
            "connection_id": str(conn.id),
            "start_time": session_row.start_time.isoformat(),
        },
        notify_user_ids=[mentor_uid, mentee_uid],
    )
    event_bus.publish_event(
        event_bus.TOPIC_CREDIT_UPDATED,
        {"user_id": str(mentee_uid), "cached_credit_score": new_balance},
        notify_user_ids=[mentee_uid],
    )
    return session_row


def reject_session_booking_request(
    db: Session,
    *,
    user: User,
    request_id: UUID,
) -> None:
    req = (
        db.query(SessionBookingRequest)
        .filter(SessionBookingRequest.id == request_id)
        .with_for_update()
        .one_or_none()
    )
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if req.status != "PENDING":
        raise HTTPException(status.HTTP_409_CONFLICT, "Request is no longer pending")

    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.id == req.connection_id)
        .one_or_none()
    )
    if not conn or conn.status != "ACTIVE":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")

    mentor = db.query(MentorProfile).filter(MentorProfile.id == conn.mentor_id).one()
    if mentor.user_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only the mentor can reject this request",
        )

    slot = (
        db.query(TimeSlot)
        .filter(TimeSlot.id == req.slot_id)
        .with_for_update()
        .one_or_none()
    )
    if slot and slot.pending_request_id == req.id:
        slot.pending_request_id = None

    req.status = "REJECTED"
    req.resolved_at = datetime.now(timezone.utc)
    db.commit()

    mentor_uid, mentee_uid = _party_user_ids(db, conn)
    event_bus.publish_connections_event(
        event_bus.TOPIC_SESSION_BOOKING_REJECTED,
        {
            "request_id": str(req.id),
            "connection_id": str(conn.id),
            "slot_id": str(req.slot_id),
            "mentor_user_id": str(mentor_uid),
            "mentee_user_id": str(mentee_uid),
        },
        notify_user_ids=[mentee_uid],
    )


async def list_incoming_session_requests(db: Session, *, user: User) -> list[dict]:
    mp = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
    if not mp:
        return []

    rows = (
        db.query(SessionBookingRequest, TimeSlot, MentorshipConnection, MenteeProfile, User)
        .join(TimeSlot, TimeSlot.id == SessionBookingRequest.slot_id)
        .join(MentorshipConnection, MentorshipConnection.id == SessionBookingRequest.connection_id)
        .join(MenteeProfile, MenteeProfile.id == MentorshipConnection.mentee_id)
        .join(User, User.id == MenteeProfile.user_id)
        .filter(
            MentorshipConnection.mentor_id == mp.id,
            MentorshipConnection.status == "ACTIVE",
            SessionBookingRequest.status == "PENDING",
        )
        .order_by(TimeSlot.start_time.asc())
        .all()
    )
    out: list[dict] = []
    for req, slot, _conn, _me, mentee_user in rows:
        local = (mentee_user.email or "").split("@")[0]
        mentee_name = local.replace(".", " ").replace("_", " ").title() or "Mentee"
        out.append(
            {
                "request_id": req.id,
                "connection_id": req.connection_id,
                "slot_id": req.slot_id,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "agreed_cost": req.agreed_cost,
                "mentee_name": mentee_name,
                "status": req.status,
            }
        )
    return out
