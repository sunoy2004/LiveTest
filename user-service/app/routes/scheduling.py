from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import MentorProfile, MentorshipConnection, User
from app.schemas import (
    BookSessionRequest,
    BookSessionResponse,
    BookingContextResponse,
    TimeSlotPublic,
)
from app.services.booking_service import (
    book_slot_saga,
    list_open_slots_for_connection,
    mentee_booking_context,
)
from app.services.mentor_pricing import resolve_mentor_session_price

router = APIRouter()


@router.get("/context", response_model=BookingContextResponse)
def scheduling_context(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ctx = mentee_booking_context(db, user=user)
    if not ctx:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No mentee booking context (mentee profile or active connection required)",
        )
    return BookingContextResponse(
        connection_id=ctx["connection_id"],
        mentor_display_name=ctx["mentor_display_name"],
        cached_credit_score=ctx["cached_credit_score"],
        slots=[TimeSlotPublic.model_validate(s) for s in ctx["slots"]],
    )


@router.get("/slots", response_model=list[TimeSlotPublic])
def scheduling_slots(
    connection_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = list_open_slots_for_connection(db, user=user, connection_id=connection_id)
    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.id == connection_id)
        .one_or_none()
    )
    if not conn or conn.status != "ACTIVE":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    mentor = db.query(MentorProfile).filter(MentorProfile.id == conn.mentor_id).one()
    price = resolve_mentor_session_price(db, mentor)
    return [
        TimeSlotPublic(
            id=r.id,
            start_time=r.start_time,
            end_time=r.end_time,
            cost_credits=price,
        )
        for r in rows
    ]


@router.post("/book", response_model=BookSessionResponse)
def scheduling_book(
    body: BookSessionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = book_slot_saga(
        db,
        user=user,
        connection_id=body.connection_id,
        slot_id=body.slot_id,
        agreed_cost=body.agreed_cost,
    )
    return BookSessionResponse(
        request_id=row["request_id"],
        session_id=row.get("session_id"),
        status=row["status"],
        meeting_url=row["meeting_url"],
        start_time=row["start_time"],
    )
