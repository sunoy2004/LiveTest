from fastapi import APIRouter

from app.routes.v1 import profiles, requests, search

api_v1_router = APIRouter()
api_v1_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_v1_router.include_router(requests.router, prefix="/requests", tags=["mentorship-requests"])
api_v1_router.include_router(search.router, tags=["search"])
