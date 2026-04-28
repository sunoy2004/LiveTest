"""GET /api/v1/profiles/me — same contract as mentor-mentee-module SPA (gateway on user-service)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import MentoringProfileMeResponse
from app.services.profile_service import get_full_profile

router = APIRouter()


@router.get("/me", response_model=MentoringProfileMeResponse)
def profiles_me(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MentoringProfileMeResponse:
    full = get_full_profile(db, user=user)
    return MentoringProfileMeResponse(
        mentee=full.mentee_profile,
        mentor=full.mentor_profile,
    )


@router.post("/mentee")
def post_mentee_profile(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.profile_service import create_or_update_mentee_profile
    return create_or_update_mentee_profile(db, user_id=user.id, body=body)
