import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import (
    MentorshipConnection,
)
from app.api.deps import require_user_id

router = APIRouter()

@router.get("/count")
async def get_active_mentorship_count(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return the count of ACTIVE mentorship connections for the authenticated user.
    Uses the new canonical user-id based schema.
    """
    count = await db.scalar(
        select(func.count())
        .select_from(MentorshipConnection)
        .where(
            or_(
                MentorshipConnection.mentee_user_id == user_id,
                MentorshipConnection.mentor_user_id == user_id
            ),
            MentorshipConnection.status == "ACTIVE",
        )
    )
    return {"active_mentorships": count or 0}

@router.get("/mentors")
async def get_active_mentors_for_user(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return mentor user_ids for the authenticated user's ACTIVE mentorship connections.
    """
    stmt = (
        select(MentorshipConnection.mentor_user_id)
        .where(
            MentorshipConnection.mentee_user_id == user_id,
            MentorshipConnection.status == "ACTIVE",
        )
    )
    results = (await db.execute(stmt)).scalars().all()
    return {"mentors": [str(uid) for uid in results]}

@router.get("/mentees")
async def get_active_mentees_for_user(
    user_id: Annotated[uuid.UUID, Depends(require_user_id)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return mentee user_ids for the authenticated user's ACTIVE mentorship connections.
    """
    stmt = (
        select(MentorshipConnection.mentee_user_id)
        .where(
            MentorshipConnection.mentor_user_id == user_id,
            MentorshipConnection.status == "ACTIVE",
        )
    )
    results = (await db.execute(stmt)).scalars().all()
    return {"mentees": [str(uid) for uid in results]}
