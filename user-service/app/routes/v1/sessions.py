from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.routes.v1.deps import get_api_v1_user

router = APIRouter()


@router.get("/incoming-requests")
async def get_incoming_session_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """Mentor fetches pending session booking requests."""
    from app.services import session_booking_request_service
    return await session_booking_request_service.list_incoming_session_requests(db, user=user)


@router.post("/requests/{request_id}/accept")
async def accept_session_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """Mentor accepts a session booking request."""
    from app.services import session_booking_request_service
    return await session_booking_request_service.accept_session_booking_request(
        db, user=user, request_id=request_id
    )


@router.post("/requests/{request_id}/reject")
async def reject_session_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """Mentor rejects a session booking request."""
    from app.services import session_booking_request_service
    await session_booking_request_service.reject_session_booking_request(
        db, user=user, request_id=request_id
    )
    return {"status": "rejected"}


@router.post("/{session_id}/history")
async def post_session_history(
    session_id: UUID,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """Mirror of mentoring-service session history endpoint."""
    from app.services.session_history_service import create_history_entry
    return await create_history_entry(db, user=user, session_id=session_id, notes=body)
