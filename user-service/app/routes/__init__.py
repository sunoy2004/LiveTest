from fastapi import APIRouter
from app.routes import auth, internal

router = APIRouter()
router.include_router(auth.router)
router.include_router(internal.router, prefix="/internal")
