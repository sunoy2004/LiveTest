import os

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

JWT_SECRET = os.getenv("JWT_SECRET", "secret")


def get_authenticated_user_id(
    creds: HTTPAuthorizationCredentials | None,
    x_user_id: str | None,
) -> str:
    """Resolves the acting user: gateway header mode or JWT subject."""
    if os.getenv("AI_TRUST_GATEWAY_HEADERS", "false").lower() == "true":
        if not (x_user_id and x_user_id.strip()):
            raise HTTPException(
                status_code=401,
                detail="X-User-Id required when AI_TRUST_GATEWAY_HEADERS is true",
            )
        return x_user_id.strip()
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        payload = jwt.decode(
            creds.credentials,
            JWT_SECRET,
            algorithms=["HS256"],
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e
    tok_uid = str(payload.get("user_id", ""))
    if not tok_uid:
        raise HTTPException(status_code=401, detail="Token missing user_id")
    if x_user_id and x_user_id.strip() and x_user_id.strip() != tok_uid:
        raise HTTPException(status_code=403, detail="X-User-Id must match token")
    return tok_uid


def verify_recommendation_caller(
    user_id: str,
    creds: HTTPAuthorizationCredentials | None,
    x_user_id: str | None,
) -> None:
    """GET /recommendations: when not in gateway-trust mode, require Bearer and user_id == subject."""
    if os.getenv("AI_TRUST_GATEWAY_HEADERS", "false").lower() == "true":
        return
    sub = get_authenticated_user_id(creds, x_user_id)
    if sub != user_id:
        raise HTTPException(status_code=403, detail="user_id must match token subject")
