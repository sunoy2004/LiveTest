import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user_id
from app.services.scheduling_service import SchedulingService

router = APIRouter()


async def get_scheduling_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SchedulingService:
    return SchedulingService(session)


class BookSessionBody(BaseModel):
    connection_id: str = Field(..., min_length=1)
    slot_id: uuid.UUID
    agreed_cost: int | None = None


@router.get("/connected-mentors")
async def get_connected_mentors(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)],
):
    """Mentees: mentors with ACTIVE connection (SPA scheduling picker)."""
    return await svc.get_connected_mentors(user_id)


@router.get("/availability")
async def get_availability(
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)],
    mentor_id: uuid.UUID | None = Query(None, description="Mentor user id (preferred)"),
    mentor_user_id: uuid.UUID | None = Query(None, description="Alias for mentor_id"),
):
    """List available (unbooked) slots for a mentor."""
    mid = mentor_id or mentor_user_id
    if mid is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Query parameter mentor_id is required",
        )
    return await svc.get_available_slots_for_mentor(mid)


@router.post("/book")
async def book_session_endpoint(
    body: BookSessionBody,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)],
):
    """Book a mentoring slot (pending mentor approval until accept)."""
    return await svc.book_session_simple(
        mentee_user_id=user_id,
        connection_id=body.connection_id,
        slot_id=body.slot_id,
    )

@router.get("/my-availability")
async def get_my_availability(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)],
):
    """List slots for the logged-in mentor."""
    return await svc.get_my_availability(user_id)

@router.post("/availability")
async def add_availability(
    body: dict,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)],
):
    """Add a new availability slot."""
    start = datetime.fromisoformat(body["start_time"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(body["end_time"].replace("Z", "+00:00"))
    return await svc.add_availability(user_id, start, end)

@router.delete("/availability/{slot_id}")
async def delete_availability(
    slot_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    svc: Annotated[SchedulingService, Depends(get_scheduling_service)],
):
    """Remove an unbooked availability slot."""
    return await svc.delete_availability(user_id, slot_id)
