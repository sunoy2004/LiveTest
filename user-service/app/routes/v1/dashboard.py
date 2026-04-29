from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db, get_mentoring_db
from app.deps import get_current_user
from app.models import User
from app.services import dashboard_service

router = APIRouter()


@router.get("/upcoming-sessions")
async def dashboard_upcoming_session(
    context: str | None = Query(None, regex="^(mentor|mentee)$"),
    db: Session = Depends(get_db),
    mentoring_db: Session = Depends(get_mentoring_db),
    user: User = Depends(get_current_user),
):
    """Next scheduled session or pending booking request."""
    return await dashboard_service.get_upcoming_sessions(db, mentoring_db, user=user, context=context)


@router.get("/goals")
async def dashboard_goals(
    context: str | None = Query(None, regex="^(mentor|mentee)$"),
    db: Session = Depends(get_db),
    mentoring_db: Session = Depends(get_mentoring_db),
    user: User = Depends(get_current_user),
):
    """Goals associated with the active mentorship connection."""
    return await dashboard_service.get_goals(db, mentoring_db, user=user, context=context)


@router.get("/vault")
async def dashboard_vault(
    context: str | None = Query(None, regex="^(mentor|mentee)$"),
    db: Session = Depends(get_db),
    mentoring_db: Session = Depends(get_mentoring_db),
    user: User = Depends(get_current_user),
):
    """Session history and notes (Vault) for the active connection."""
    return await dashboard_service.get_vault(db, mentoring_db, user=user, context=context)


@router.get("/stats")
async def dashboard_stats(
    context: str | None = Query(None, regex="^(mentor|mentee)$"),
    db: Session = Depends(get_db),
    mentoring_db: Session = Depends(get_mentoring_db),
    user: User = Depends(get_current_user),
):
    """Aggregate stats for the dashboard (hours, partners, etc.)."""
    return await dashboard_service.get_dashboard_stats(db, mentoring_db, user=user, context=context)
