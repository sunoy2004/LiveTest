import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_mentorship_request_service, require_user_id
from app.schemas.request import MentorshipRequestCreate, MentorshipRequestRead, MentorshipRequestStatusUpdate
from app.services.mentorship_request_service import MentorshipRequestService

router = APIRouter()


@router.post("", response_model=MentorshipRequestRead, status_code=status.HTTP_201_CREATED)
async def create_mentorship_request(
    body: MentorshipRequestCreate,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> MentorshipRequestRead:
    """Mentee (by X-User-Id) requests a mentor. Enforces DPDP consent before create."""
    req = await svc.create_request(user_id, body)
    return MentorshipRequestRead.model_validate(req)


@router.get("/incoming", response_model=list[MentorshipRequestRead])
async def get_incoming_requests(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> list[MentorshipRequestRead]:
    """Mentor (by X-User-Id) fetches requests sent to them."""
    reqs = await svc.get_incoming_requests(user_id)
    return [MentorshipRequestRead(**r) for r in reqs]


@router.get("/outgoing", response_model=list[MentorshipRequestRead])
async def get_outgoing_requests(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> list[MentorshipRequestRead]:
    """Mentee (by X-User-Id) fetches requests they sent."""
    reqs = await svc.get_outgoing_requests(user_id)
    return [MentorshipRequestRead(**r) for r in reqs]


@router.get("/connections", response_model=list[MentorshipRequestRead])
async def get_active_connections(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> list[MentorshipRequestRead]:
    """Fetch active connections for the user (bridge for User Service dashboard)."""
    reqs = await svc.get_active_connections(user_id)
    return [MentorshipRequestRead(**r) for r in reqs]


@router.get("/admin/connections", response_model=list[dict])
async def admin_get_all_connections(
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> list[dict]:
    """Fetch ALL active connections across the platform for admin view."""
    return await svc.admin_list_all_connections()


@router.put("/{request_id}/status", response_model=MentorshipRequestRead)
async def update_mentorship_request_status(
    request_id: uuid.UUID,
    body: MentorshipRequestStatusUpdate,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> MentorshipRequestRead:
    """Mentor accepts or declines. On ACCEPT, creates connection and publishes stub event."""
    req = await svc.update_status(request_id, user_id, body)
    return MentorshipRequestRead.model_validate(req)
