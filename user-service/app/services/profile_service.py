from sqlalchemy.orm import Session
from app.models import User
from app.schemas import (
    FullProfileResponse,
    UserPublic,
)

def build_user_public(_db: Session, *, user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        is_admin=(user.role == "ADMIN"),
    )


def get_full_profile(db: Session, *, user: User) -> FullProfileResponse:
    # Profiles are now handled by the Mentoring Service.
    # We return basic user info from User Service.
    return FullProfileResponse(
        user_id=user.id,
        email=user.email,
        is_admin=(user.role == "ADMIN"),
        mentor_profile=None,
        mentee_profile=None,
    )
