from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from app.deps import get_current_user
from app.models import User


def get_api_v1_user(
    user: User = Depends(get_current_user),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> User:
    if x_user_id and x_user_id.strip():
        try:
            hid = UUID(x_user_id.strip())
        except ValueError as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-User-Id",
            ) from e
        if hid != user.id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="X-User-Id must match authenticated user",
            )
    return user
