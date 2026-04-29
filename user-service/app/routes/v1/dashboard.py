from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.services import dashboard_service
from app.services.mentoring_client import (
    get_active_mentorship_count,
    get_mentor_user_ids,
)

router = APIRouter()


@router.get("/active-mentorships")
async def dashboard_active_mentorships(
    user: User = Depends(get_current_user),
):
    """
    Active mentorship count — sourced exclusively from the Mentoring Service.

    The User Service does NOT query its own DB for this data.
    Instead, it calls GET mentoring-service/api/v1/mentorships/count?user_id=...
    and returns the result directly to the UI.

    Fallback: returns 0 if the Mentoring Service is unreachable.
    """
    count = await get_active_mentorship_count(user.id)
    return {"active_mentorships": count}


@router.get("/upcoming-sessions")
async def dashboard_upcoming_sessions(
    context: str | None = Query(None, regex="^(mentor|mentee)$"),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Upcoming sessions — hybrid source with correct service boundaries.

    Step 1: Fetch sessions from User Service DB (sessions table)
    Step 2: Fetch valid mentors from Mentoring Service API
    Step 3: Filter sessions to only those with valid mentor relationships
    Step 4: Return filtered sessions to UI

    Fallback: returns empty list if no mentors or Mentoring Service is unreachable.
    """
    return await dashboard_service.get_upcoming_sessions_filtered(
        db, user=user, context=context, limit=limit,
    )



@router.get("/goals")
async def dashboard_goals(
    context: str | None = Query(None, regex="^(mentor|mentee)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Goals associated with the active mentorship connection."""
    return await dashboard_service.get_goals(db, user=user, context=context)


@router.get("/vault")
async def dashboard_vault(
    context: str | None = Query(None, regex="^(mentor|mentee)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Session history and notes (Vault) for the active connection."""
    return await dashboard_service.get_vault(db, user=user, context=context)


@router.get("/stats")
async def dashboard_stats(
    context: str | None = Query(None, regex="^(mentor|mentee)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Aggregate stats for the dashboard (hours, partners, etc.)."""
    return await dashboard_service.get_dashboard_stats(db, user=user, context=context)

