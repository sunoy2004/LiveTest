from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    MentorshipRequestCreate,
    MentorshipRequestRead,
    MentorshipRequestStatusUpdate,
    MentorshipRequestIncomingItem,
)
from app.routes.v1.deps import get_api_v1_user
from app.models import User
from app.services import mentorship_request_service as mrs

router = APIRouter()


@router.post(
    "",
    response_model=MentorshipRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_mentorship_request(
    body: MentorshipRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    req = mrs.create_request(
        db,
        mentee_user_id=user.id,
        mentor_profile_id=body.mentor_id,
        intro_message=body.intro_message,
    )
    return MentorshipRequestRead.model_validate(req)


@router.put("/{request_id}/status", response_model=MentorshipRequestRead)
def update_mentorship_request_status(
    request_id: UUID,
    body: MentorshipRequestStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    req = mrs.update_request_status(
        db,
        request_id=request_id,
        acting_user_id=user.id,
        new_status=body.status,
    )
    return MentorshipRequestRead.model_validate(req)


@router.get("/incoming", response_model=list[MentorshipRequestIncomingItem])
def list_incoming_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    results = mrs.list_incoming_requests(db, mentor_user_id=user.id)
    return [MentorshipRequestIncomingItem.model_validate(r) for r in results]
