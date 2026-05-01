import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app.api.deps import require_user_id, get_db
from app.services.dashboard_service import DashboardService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class GoalCreateBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=2000, description="Quest / goal description")


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

@router.get("/upcoming-session")
async def dashboard_upcoming_session(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> dict | None:
    """One next session — aligns with SPA `GET .../dashboard/upcoming-session`."""
    rows = await svc.get_upcoming_sessions(user_id, limit=1)
    return rows[0] if rows else None


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


@router.post("/goals", status_code=status.HTTP_201_CREATED)
async def dashboard_create_goal(
    body: GoalCreateBody,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> dict:
    """Create a personal learning goal (quest) for the authenticated user."""
    return await svc.create_goal(user_id, body.title)


@router.get("/vault")
async def dashboard_vault(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> list[dict]:
    return await svc.get_vault(user_id)


@router.get("/session-booking-requests")
async def dashboard_session_booking_requests(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    """Ledger of `session_booking_requests` involving the current user."""
    return await svc.get_session_booking_request_ledger(user_id, limit=limit)
