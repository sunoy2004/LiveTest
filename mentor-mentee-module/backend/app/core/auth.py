import os
from typing import Any
from uuid import UUID

import jwt

from app.core.config import settings

def verify_token(token: str) -> dict[str, Any]:
    """Verify JWT token and return payload."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except Exception as e:
        raise ValueError(f"Invalid or expired token: {str(e)}")
