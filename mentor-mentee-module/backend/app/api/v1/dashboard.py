import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from app.api.deps import require_user_id, get_db
from app.services.dashboard_service import DashboardService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

async def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardService:
    return DashboardService(session)

@router.get("/stats")
async def dashboard_stats(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> dict:
    return await svc.get_stats(user_id)

@router.get("/upcoming-sessions")
async def dashboard_upcoming_sessions(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
    limit: int = Query(5, ge=1, le=20),
) -> list[dict]:
    return await svc.get_upcoming_sessions(user_id, limit=limit)

@router.get("/goals")
async def dashboard_goals(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> list[dict]:
    return await svc.get_goals(user_id)

@router.get("/vault")
async def dashboard_vault(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> list[dict]:
    return await svc.get_vault(user_id)
