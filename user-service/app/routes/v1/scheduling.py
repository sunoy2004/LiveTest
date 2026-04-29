from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.routes.v1.deps import get_api_v1_user
from app.services import scheduling_service, booking_service

router = APIRouter()


@router.get("/connected-mentors")
async def get_connected_mentors(
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """List mentors the current mentee is connected to."""
    return await scheduling_service.get_connected_mentors_for_mentee(db, user=user)


@router.get("/availability")
async def get_availability(
    mentor_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """Mirror of mentoring-service availability endpoint."""
    return await scheduling_service.get_available_slots_for_mentor(
        db, user=user, mentor_id=mentor_id
    )


@router.post("/book")
async def post_book(
    body: dict, # Using dict to be flexible with the incoming body
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """Mirror of mentoring-service book endpoint."""
    # The frontend sends connection_id and slot_id
    return await scheduling_service.book_session_simple(
        db,
        user=user,
        connection_id=UUID(body["connection_id"]),
        slot_id=UUID(body["slot_id"]),
    )


@router.get("/my-availability")
async def get_my_availability(
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """List current slots for the logged-in mentor."""
    return await scheduling_service.get_my_availability(db, user=user)


@router.post("/availability")
async def add_availability(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """Add a new availability slot."""
    from datetime import datetime
    start = datetime.fromisoformat(body["start_time"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(body["end_time"].replace("Z", "+00:00"))
    return await scheduling_service.add_availability(
        db, user=user, start_time=start, end_time=end
    )


@router.delete("/availability/{slot_id}")
async def delete_availability(
    slot_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """Remove an unbooked availability slot."""
    return await scheduling_service.delete_availability(db, user=user, slot_id=slot_id)
