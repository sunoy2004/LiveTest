from fastapi import APIRouter
from app.routes.v1 import dashboard, profiles, requests, scheduling, search, sessions

api_v1_router = APIRouter()
api_v1_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_v1_router.include_router(requests.router, prefix="/requests", tags=["mentorship-requests"])
api_v1_router.include_router(search.router, tags=["search"])
api_v1_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_v1_router.include_router(scheduling.router, prefix="/scheduling", tags=["scheduling"])
api_v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])



