from __future__ import annotations

import os
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_ALGORITHM = "HS256"
INTERNAL_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")

security = HTTPBearer(auto_error=False)


def _decode_jwt(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


async def get_current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> UUID:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = _decode_jwt(creds.credentials)
        return UUID(str(payload["user_id"]))
    except Exception as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
        ) from exc


def require_admin_session(request: Request) -> None:
    """Cookie session set by POST /admin/auth/login (gamification admin UI only)."""
    if not request.session.get("gamification_admin"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def require_internal_token(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
) -> None:
    if not INTERNAL_TOKEN or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid internal token")
