from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, User
from app.schemas import (
    FullProfileResponse,
    MenteeProfilePublic,
    MentorProfilePublic,
    UserPublic,
)
def build_user_public(_db: Session, *, user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        is_admin=(user.role == "ADMIN"),
    )


def get_full_profile(db: Session, *, user: User) -> FullProfileResponse:
    mentor_row = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
    mentee_row = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()

    mentor_out = MentorProfilePublic.model_validate(mentor_row) if mentor_row else None
    mentee_out = MenteeProfilePublic.model_validate(mentee_row) if mentee_row else None

    return FullProfileResponse(
        user_id=user.id,
        email=user.email,
        is_admin=(user.role == "ADMIN"),
        mentor_profile=mentor_out,
        mentee_profile=mentee_out,
    )
