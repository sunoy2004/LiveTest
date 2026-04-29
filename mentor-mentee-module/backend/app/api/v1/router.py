from fastapi import APIRouter

from app.api.v1 import mentorships, profiles, requests, search, dashboard

api_router = APIRouter()
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(requests.router, prefix="/requests", tags=["mentorship-requests"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(mentorships.router, prefix="/mentorships", tags=["mentorships"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
