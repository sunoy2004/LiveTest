import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_profile_service, require_user_id
from app.schemas.profile import (
    MenteeProfileCreate,
    MenteeProfileRead,
    MentorProfileCreate,
    MentorProfileRead,
    ProfileMeResponse,
)
from app.services.profile_service import ProfileService

router = APIRouter()


@router.post("/mentee", response_model=MenteeProfileRead, status_code=status.HTTP_201_CREATED)
async def create_mentee_profile(
    body: MenteeProfileCreate,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[ProfileService, Depends(get_profile_service)],
) -> MenteeProfileRead:
    """Create mentee profile. Minors get guardian_consent_status=PENDING (DPDP)."""
    profile = await svc.create_mentee_profile(user_id, body)
    return MenteeProfileRead.model_validate(profile)


@router.post("/mentor", response_model=MentorProfileRead, status_code=status.HTTP_201_CREATED)
async def create_mentor_profile(
    body: MentorProfileCreate,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[ProfileService, Depends(get_profile_service)],
) -> MentorProfileRead:
    """Register a mentor (same gateway contract as mentee). Tiers must exist in DB."""
    profile = await svc.create_mentor_profile(user_id, body)
    return MentorProfileRead.model_validate(profile)


@router.get("/me", response_model=ProfileMeResponse)
async def get_my_profiles(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileMeResponse:
    mentee, mentor = await svc.get_profile_bundle(user_id)
    user = await svc._session.get(User, user_id)
    return ProfileMeResponse(
        mentee_profile=mentee,
        mentor_profile=mentor,
        is_admin=user.is_admin if user else False
    )
