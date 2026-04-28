from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.routes.v1.deps import get_api_v1_user

router = APIRouter()


@router.post("/{session_id}/history")
async def post_session_history(
    session_id: UUID,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_api_v1_user),
):
    """Mirror of mentoring-service session history endpoint."""
    from app.services.session_history_service import create_history_entry
    return await create_history_entry(db, user=user, session_id=session_id, notes=body)
