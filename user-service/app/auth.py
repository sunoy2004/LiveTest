import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import bcrypt
import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash. Supports bcrypt and plain-text fallback for demo data."""
    try:
        # Standard bcrypt check
        if hashed.startswith("$2") or len(hashed) > 32: # Likely a hash
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        pass
    
    # Fallback: exact match (useful for seeded/demo accounts with plain text 'passwords')
    return plain == hashed


def create_token(
    user_id: UUID,
    email: str,
    role: str,
    *,
    is_admin: bool = False,
) -> str:
    now = datetime.now(timezone.utc)
    iat = int(now.timestamp())
    exp = iat + ACCESS_TOKEN_EXPIRE_MINUTES * 60
    payload: dict[str, Any] = {
        "user_id": str(user_id),
        "email": email,
        "role": role,
        "is_admin": is_admin,
        "iat": iat,
        "exp": exp,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
