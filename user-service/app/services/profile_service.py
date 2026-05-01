from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserPublic


def build_user_public(_db: Session, *, user: User) -> UserPublic:
    raw_roles = user.role or []
    roles = [str(r) for r in raw_roles] if raw_roles is not None else []
    return UserPublic(
        id=user.id,
        email=user.email,
        is_admin=("ADMIN" in roles),
        roles=roles,
    )
