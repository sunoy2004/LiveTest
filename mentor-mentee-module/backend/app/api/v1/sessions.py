import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user_id
from app.services.session_service import SessionMeetingFieldsBody, SessionService

router = APIRouter()


async def get_session_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SessionService:
    return SessionService(session)


@router.get("/incoming-requests")
async def incoming_session_requests(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SessionService, Depends(get_session_service)],
):
    """Mentors: pending session bookings from mentees."""
    return await svc.list_incoming_booking_requests(user_id)


@router.post("/requests/{request_id}/accept")
async def accept_session_booking_request(
    request_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SessionService, Depends(get_session_service)],
):
    return await svc.accept_booking_request(user_id, request_id)


@router.post("/requests/{request_id}/reject")
async def reject_session_booking_request(
    request_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SessionService, Depends(get_session_service)],
):
    await svc.reject_booking_request(user_id, request_id)
    return {"status": "rejected"}


@router.get("")
async def get_sessions(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SessionService, Depends(get_session_service)],
):
    return await svc.get_upcoming_sessions(user_id)


@router.patch("/{session_id}/meeting-fields", status_code=status.HTTP_200_OK)
async def patch_session_meeting_fields(
    session_id: uuid.UUID,
    body: SessionMeetingFieldsBody,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SessionService, Depends(get_session_service)],
):
    """Shared meeting notes and outcome — mentor and mentee may update."""
    return await svc.update_session_meeting_fields(user_id, session_id, body)


@router.post("/{session_id}/history")
async def post_session_history(
    session_id: uuid.UUID,
    body: dict,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SessionService, Depends(get_session_service)],
):
    return await svc.create_session_history(user_id, session_id, body)
