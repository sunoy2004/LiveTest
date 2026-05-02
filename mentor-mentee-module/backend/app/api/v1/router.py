from fastapi import APIRouter

from app.api.v1 import admin, mentorships, profiles, requests, search, dashboard, scheduling, sessions, internal

api_router = APIRouter()
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(requests.router, prefix="/requests", tags=["mentorship-requests"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(mentorships.router, prefix="/mentorships", tags=["mentorships"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(scheduling.router, prefix="/scheduling", tags=["scheduling"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(internal.router, prefix="/internal", tags=["internal"])
