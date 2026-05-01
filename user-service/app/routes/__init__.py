"""
User Service HTTP surface: authentication and internal helpers only.

Domain data (profiles, dashboard, scheduling, sessions, search) is served by the
Mentoring Service using the same JWT (user_id + roles). Do not mount mentoring
routes here — the UI should call the mentoring base URL for `/api/v1/...`.
"""

from fastapi import APIRouter

from app.routes import auth, internal

router = APIRouter()
router.include_router(auth.router)
router.include_router(internal.router, prefix="/internal")
