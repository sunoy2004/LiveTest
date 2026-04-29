import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.mentorship_request_service import MentorshipRequestService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService


from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core import auth

security = HTTPBearer(auto_error=False)

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from app.models.user import User

async def require_user_id(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> uuid.UUID:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = auth.verify_token(creds.credentials)
        uid = uuid.UUID(payload["user_id"])
        
        # Sync User replica
        # Architecture Rule: Mentoring DB keeps a replica of users
        # user_id is the universal identifier
        stmt = insert(User).values(
            user_id=uid,
            email=payload["email"],
            role=payload["role"],
            password_hash="[REDACTED]" # Not needed in replica but schema requires it
        ).on_conflict_do_update(
            index_elements=[User.user_id],
            set_={
                "email": payload["email"],
                "role": payload["role"]
            }
        )
        await db.execute(stmt)
        await db.commit()
        
        return uid
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


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
