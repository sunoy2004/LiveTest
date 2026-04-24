from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import SessionCompleteResponse, UpcomingSessionItem
from app.services import dashboard_service
from app.services.session_completion_service import complete_session

router = APIRouter(tags=["sessions"])


@router.get("/sessions/upcoming", response_model=list[UpcomingSessionItem])
def sessions_upcoming(
    context: str | None = Query(None, description="mentor | mentee"),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return dashboard_service.get_upcoming_sessions(db, user=user, context=context, limit=limit)


@router.post("/sessions/{session_id}/complete", response_model=SessionCompleteResponse)
def complete_session_route(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = complete_session(db, user=user, session_id=session_id)
    return SessionCompleteResponse(session_id=row.id, status=row.status)
