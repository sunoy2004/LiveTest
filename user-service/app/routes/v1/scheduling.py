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
