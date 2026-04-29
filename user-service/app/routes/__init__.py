from fastapi import APIRouter

from app.routes import admin, auth, internal, mentoring, scheduling, sessions, wallet
from app.routes.v1 import api_v1_router

router = APIRouter()
router.include_router(auth.router)
router.include_router(admin.router)
router.include_router(wallet.router)
router.include_router(internal.router, prefix="/internal")
