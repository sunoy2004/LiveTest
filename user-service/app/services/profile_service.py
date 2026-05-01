from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserPublic


def build_user_public(_db: Session, *, user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        is_admin=("ADMIN" in (user.role or [])),
    )
