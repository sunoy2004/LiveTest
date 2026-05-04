import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_profile_service, jwt_email_from_bearer, require_user_id
from app.schemas.profile import (
    MenteeProfileCreate,
    MenteeProfileRead,
    MentorProfileCreate,
    MentorProfileRead,
    ProfileMeResponse,
)
from app.services.profile_service import ProfileService
from app.models.user import User
from app.utils.display_name import split_local_parts

router = APIRouter()


@router.get("/mentor/{mentor_user_id}")
async def get_mentor_detail(
    mentor_user_id: uuid.UUID,
    _viewer: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[ProfileService, Depends(get_profile_service)],
) -> dict:
    """Mentor profile for modals; `mentor_user_id` is the mentoring `users.user_id` UUID."""
    payload = await svc.get_mentor_public_detail(mentor_user_id)
    if payload is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentor profile not found")
    return payload


def _mentee_read(profile, email: str | None) -> MenteeProfileRead:
    fn, ln = split_local_parts(email)
    return MenteeProfileRead(
        user_id=profile.user_id,
        first_name=fn,
        last_name=ln,
        learning_goals=list(profile.learning_goals or []),
        education_level=profile.education_level,
        cached_credit_score=int(profile.cached_credit_score or 0),
    )


def _mentor_read(profile, email: str | None) -> MentorProfileRead:
    fn, ln = split_local_parts(email)
    return MentorProfileRead(
        user_id=profile.user_id,
        first_name=fn,
        last_name=ln,
        bio=profile.bio,
        expertise=list(profile.expertise or []),
        experience_years=profile.experience_years or 0,
    )


@router.post("/mentee", response_model=MenteeProfileRead, status_code=status.HTTP_201_CREATED)
async def create_mentee_profile(
    body: MenteeProfileCreate,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    token_email: Annotated[str, Depends(jwt_email_from_bearer)],
    svc: Annotated[ProfileService, Depends(get_profile_service)],
) -> MenteeProfileRead:
    """Create mentee profile (data lives in mentoring_db; user row synced from JWT)."""
    profile = await svc.create_mentee_profile(user_id, body)
    return _mentee_read(profile, token_email)


@router.post("/mentor", response_model=MentorProfileRead, status_code=status.HTTP_201_CREATED)
async def create_mentor_profile(
    body: MentorProfileCreate,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    token_email: Annotated[str, Depends(jwt_email_from_bearer)],
    svc: Annotated[ProfileService, Depends(get_profile_service)],
) -> MentorProfileRead:
    """Register a mentor."""
    profile = await svc.create_mentor_profile(user_id, body)
    return _mentor_read(profile, token_email)


@router.get("/me", response_model=ProfileMeResponse)
async def get_my_profiles(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    token_email: Annotated[str, Depends(jwt_email_from_bearer)],
    svc: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileMeResponse:
    mentee, mentor = await svc.get_profile_bundle(user_id)
    user = await svc._session.get(User, user_id)
    return ProfileMeResponse(
        mentee_profile=_mentee_read(mentee, token_email) if mentee else None,
        mentor_profile=_mentor_read(mentor, token_email) if mentor else None,
        is_admin="ADMIN" in (user.role or []) if user else False,
    )
