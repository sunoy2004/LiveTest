import uuid
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from app.api.deps import require_user_id, get_db
from app.services.scheduling_service import SchedulingService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

async def get_scheduling_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SchedulingService:
    return SchedulingService(session)

@router.get("/availability")
async def get_availability(
    mentor_user_id: uuid.UUID = Query(...),
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)] = None,
):
    """List available slots for a mentor."""
    return await svc.get_available_slots_for_mentor(mentor_user_id)

@router.get("/my-availability")
async def get_my_availability(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)] = None,
):
    """List slots for the logged-in mentor."""
    return await svc.get_my_availability(user_id)

@router.post("/availability")
async def add_availability(
    body: dict,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)] = None,
):
    """Add a new availability slot."""
    start = datetime.fromisoformat(body["start_time"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(body["end_time"].replace("Z", "+00:00"))
    return await svc.add_availability(user_id, start, end)

@router.delete("/availability/{slot_id}")
async def delete_availability(
    slot_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)] = None,
):
    """Remove an unbooked availability slot."""
    return await svc.delete_availability(user_id, slot_id)
