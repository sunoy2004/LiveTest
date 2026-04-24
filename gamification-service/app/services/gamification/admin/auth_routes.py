from __future__ import annotations

import hashlib
import os
import secrets

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

SESSION_KEY = "gamification_admin"

_admin_user = os.getenv("GAMIFICATION_ADMIN_USERNAME", "").strip()
_admin_pass = os.getenv("GAMIFICATION_ADMIN_PASSWORD", "").strip()


class AdminLoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


def _admin_login_configured() -> bool:
    return bool(_admin_user and _admin_pass)


def _digest(s: str) -> bytes:
    return hashlib.sha256(s.encode("utf-8")).digest()


@router.post("/login")
async def admin_login(request: Request, body: AdminLoginBody) -> dict:
    if not _admin_login_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gamification admin login is not configured (set GAMIFICATION_ADMIN_USERNAME and GAMIFICATION_ADMIN_PASSWORD)",
        )
    if not secrets.compare_digest(_digest(body.username), _digest(_admin_user)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not secrets.compare_digest(_digest(body.password), _digest(_admin_pass)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    request.session[SESSION_KEY] = True
    return {"ok": True}


@router.post("/logout")
async def admin_logout(request: Request) -> dict:
    request.session.pop(SESSION_KEY, None)
    return {"ok": True}


@router.get("/status")
async def admin_auth_status(request: Request) -> dict:
    return {"authenticated": bool(request.session.get(SESSION_KEY))}
