from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import MentorProfile, User
from app.schemas import (
    AvailableSlotItem,
    BookSessionSimpleRequest,
    BookSessionSimpleResponse,
    ConnectedMentorItem,
    MentorProfileDetail,
    MentorProfilePublic,
    SessionBookingRequestIncomingItem,
)
from app.services.scheduling_service import (
    book_session_simple,
    get_available_slots_for_mentor,
    get_connected_mentors_for_mentee,
)
from app.services.session_booking_request_service import (
    accept_session_booking_request,
    list_incoming_session_requests,
    reject_session_booking_request,
)

router = APIRouter()


def _display_name(email: str) -> str:
    local = (email or "").split("@", 1)[0]
    return local.replace("_", " ").replace(".", " ").title() or "Mentor"


@router.get("/mentor/{mentor_profile_id}", response_model=MentorProfileDetail)
def mentor_profile_detail(
    mentor_profile_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = (
        db.query(MentorProfile, User.email)
        .join(User, MentorProfile.user_id == User.id)
        .filter(MentorProfile.id == mentor_profile_id)
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentor profile not found")
    mp, email = row
    return MentorProfileDetail(
        mentor_profile=MentorProfilePublic.model_validate(mp),
        email=email or "",
        display_name=_display_name(email or ""),
    )


@router.get("/connected-mentors", response_model=list[ConnectedMentorItem])
def connected_mentors(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = get_connected_mentors_for_mentee(db, user=user)
    return [ConnectedMentorItem.model_validate(r) for r in rows]


@router.get("/availability", response_model=list[AvailableSlotItem])
def availability(
    mentor_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = get_available_slots_for_mentor(db, user=user, mentor_id=mentor_id)
    return [AvailableSlotItem.model_validate(r) for r in rows]


@router.post("/book", response_model=BookSessionSimpleResponse)
def book(
    body: BookSessionSimpleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = book_session_simple(
        db,
        user=user,
        connection_id=body.connection_id,
        slot_id=body.slot_id,
    )
    return BookSessionSimpleResponse(
        request_id=row["request_id"],
        session_id=row.get("session_id"),
        status=row["status"],
        meeting_url=row["meeting_url"],
        start_time=row["start_time"],
    )


@router.get("/incoming-session-requests", response_model=list[SessionBookingRequestIncomingItem])
def incoming_session_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = list_incoming_session_requests(db, user=user)
    return [SessionBookingRequestIncomingItem.model_validate(r) for r in rows]


@router.post("/session-requests/{request_id}/accept")
def accept_session_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session_row = accept_session_booking_request(db, user=user, request_id=request_id)
    return {
        "session_id": session_row.id,
        "status": session_row.status,
        "meeting_url": session_row.meeting_url,
        "start_time": session_row.start_time,
    }


@router.post("/session-requests/{request_id}/reject")
def reject_session_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reject_session_booking_request(db, user=user, request_id=request_id)
    return {"ok": True}
