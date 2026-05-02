import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import auth
from app.db.session import get_db
from app.models.user import User
from app.services.mentorship_request_service import MentorshipRequestService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService

security = HTTPBearer(auto_error=False)


def _roles_from_payload(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("role", [])
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw] if raw else []
    if isinstance(raw, list):
        return [str(x) for x in raw if x is not None]
    return []


def _jwt_claims_admin(payload: dict[str, Any]) -> bool:
    """Align with User Service: role contains ADMIN and/or is_admin on the token."""
    if payload.get("is_admin") is True:
        return True
    return "ADMIN" in _roles_from_payload(payload)


async def require_admin(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> None:
    """Bearer JWT from User Service — ADMIN role or is_admin."""
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = auth.verify_token(creds.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e!s}",
        ) from e
    if not _jwt_claims_admin(payload):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin only")


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
        if not payload or "user_id" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token payload")
            
        try:
            uid = uuid.UUID(payload["user_id"])
        except ValueError:
            raise HTTPException(status_code=401, detail=f"Invalid user_id format: {payload.get('user_id')}")
        
        # Defensive role handling
        raw_role = payload.get("role", [])
        role_array = raw_role if isinstance(raw_role, list) else [raw_role] if raw_role else []

        # Sync User replica
        try:
            stmt = insert(User).values(
                user_id=uid,
                email=payload["email"],
                role=role_array,
                password_hash="[REDACTED]"
            ).on_conflict_do_update(
                index_elements=[User.user_id],
                set_={
                    "email": payload["email"],
                    "role": role_array,
                }
            )
            await db.execute(stmt)
            await db.commit()
        except Exception as db_exc:
            # If DB sync fails, we LOG it but might allow the request if the user already exists?
            # Actually, better to fail and fix the schema.
            print(f"DATABASE SYNC ERROR: {str(db_exc)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database synchronization failed: {str(db_exc)}"
            )
        
        return uid
    except HTTPException:
        raise
    except Exception as e:
        print(f"AUTH ERROR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
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
