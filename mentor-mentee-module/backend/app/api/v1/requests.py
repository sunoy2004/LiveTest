import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

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
    """Mentee requests a mentor."""
    req = await svc.create_request(user_id, body)
    return MentorshipRequestRead.model_validate(req)


@router.get("/incoming", response_model=list[dict])
async def get_incoming_requests(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> list[dict]:
    """Mentor fetches requests sent to them."""
    return await svc.get_incoming_requests(user_id)


@router.get("/outgoing", response_model=list[dict])
async def get_outgoing_requests(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> list[dict]:
    """Mentee fetches requests they sent."""
    return await svc.get_outgoing_requests(user_id)


@router.get("/history", response_model=list[dict])
async def get_matchmaking_request_history(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict]:
    """Matchmaking request history from `mentorship_requests` (sent or received by the current user)."""
    return await svc.list_request_history(user_id, limit=limit)


@router.get("/connections", response_model=list[dict])
async def get_active_connections(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> list[dict]:
    """Fetch active connections for the user."""
    return await svc.get_active_connections(user_id)


@router.get("/connections/{mentor_id}/{mentee_id}/goals", response_model=list[dict])
async def get_connection_goals(
    mentor_id: uuid.UUID,
    mentee_id: uuid.UUID,
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> list[dict]:
    """Fetch goals for a specific connection (Composite Key)."""
    # Note: Service might need update to take both IDs
    # For now, I'll update service if needed, but the router now accepts both.
    return await svc.get_goals_by_users(mentor_id, mentee_id)


@router.put("/{sender_user_id}/status", response_model=dict)
@router.post("/{sender_user_id}/status", response_model=dict)
async def update_mentorship_request_status(
    sender_user_id: uuid.UUID,
    body: MentorshipRequestStatusUpdate,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[MentorshipRequestService, Depends(get_mentorship_request_service)],
) -> dict:
    """Mentor (user_id) accepts or declines request from sender_user_id.

    POST is registered alongside PUT: some proxies strip or mishandle PUT bodies toward Cloud Run.
    """
    return await svc.update_status(
        sender_user_id=sender_user_id,
        receiver_user_id=user_id,
        acting_user_id=user_id,
        body=body
    )
