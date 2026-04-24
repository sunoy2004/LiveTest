import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.mentorship_request_service import MentorshipRequestService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService


async def require_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> uuid.UUID:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id header is required",
        )
    try:
        return uuid.UUID(x_user_id.strip())
    except ValueError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-User-Id (must be UUID)",
        ) from e


async def get_profile_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileService:
    return ProfileService(session)


async def get_mentorship_request_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MentorshipRequestService:
    return MentorshipRequestService(session)


async def get_search_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SearchService:
    return SearchService(session)
