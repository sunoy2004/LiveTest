import uuid
from typing import Annotated
from fastapi import APIRouter, Depends
from app.api.deps import require_user_id, get_db
from app.services.session_service import SessionService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

async def get_session_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SessionService:
    return SessionService(session)

@router.get("")
async def get_sessions(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SessionService, Depends(get_session_service)] = None,
):
    return await svc.get_upcoming_sessions(user_id)

@router.post("/{session_id}/history")
async def post_session_history(
    session_id: uuid.UUID,
    body: dict,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SessionService, Depends(get_session_service)] = None,
):
    return await svc.create_session_history(user_id, session_id, body)
