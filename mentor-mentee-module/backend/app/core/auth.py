import os
from typing import Any
from uuid import UUID

import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_ALGORITHM = "HS256"

def verify_token(token: str) -> dict[str, Any]:
    """Verify JWT token and return payload."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as e:
        raise ValueError(f"Invalid or expired token: {str(e)}")
