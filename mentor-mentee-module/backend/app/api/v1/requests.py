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
