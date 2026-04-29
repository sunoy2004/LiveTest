"""
Mentorships API — dedicated endpoints for cross-service data contracts.

These endpoints are consumed by the User Service (and potentially other services)
to enforce service boundaries. The Mentoring Service is the sole owner of
mentorship_connections, mentor_profiles, and mentee_profiles data.

Data Contracts:
  GET /mentorships/count?user_id=<uuid>  → { "active_mentorships": int }
  GET /mentorships/mentors?user_id=<uuid> → { "mentors": [str] }
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import (
    MenteeProfile,
    MentorProfile,
    MentorshipConnection,
    MentorshipConnectionStatus,
)

router = APIRouter()


@router.get("/count")
async def get_active_mentorship_count(
    user_id: uuid.UUID = Query(..., description="The user_id to look up"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return the count of ACTIVE mentorship connections for a user.

    Logic:
      - Find mentee_profiles.id WHERE user_id = :user_id
      - Find mentor_profiles.id WHERE user_id = :user_id
      - COUNT(*) FROM mentorship_connections
        WHERE (mentee_id = :mentee_id OR mentor_id = :mentor_id) AND status = 'ACTIVE'

    If user is both mentor and mentee, both roles are counted.
    """
    mentee = await db.scalar(
        select(MenteeProfile.id).where(MenteeProfile.user_id == user_id)
    )
    mentor = await db.scalar(
        select(MentorProfile.id).where(MentorProfile.user_id == user_id)
    )

    if mentee is None and mentor is None:
        return {"active_mentorships": 0}

    # Build OR conditions based on which profiles exist
    conditions = []
    if mentee is not None:
        conditions.append(MentorshipConnection.mentee_id == mentee)
    if mentor is not None:
        conditions.append(MentorshipConnection.mentor_id == mentor)

    count = await db.scalar(
        select(func.count())
        .select_from(MentorshipConnection)
        .where(
            or_(*conditions),
            MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE,
        )
    )

    return {"active_mentorships": count or 0}


@router.get("/mentors")
async def get_active_mentors_for_user(
    user_id: uuid.UUID = Query(..., description="The mentee user_id to look up"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return mentor user_ids for a user's ACTIVE mentorship connections.

    Logic:
      - Find mentee_profiles.id WHERE user_id = :user_id
      - SELECT mentor_profiles.user_id AS mentor_user_id
        FROM mentorship_connections mc
        JOIN mentor_profiles mt ON mc.mentor_id = mt.id
        JOIN mentee_profiles mp ON mc.mentee_id = mp.id
        WHERE mp.user_id = :user_id AND mc.status = 'ACTIVE'

    Returns:
      { "mentors": ["mentor_user_id_1", "mentor_user_id_2", ...] }
    """
    mentee = await db.scalar(
        select(MenteeProfile.id).where(MenteeProfile.user_id == user_id)
    )

    if mentee is None:
        return {"mentors": []}

    stmt = (
        select(MentorProfile.user_id)
        .select_from(MentorshipConnection)
        .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
        .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
        .where(
            MenteeProfile.user_id == user_id,
            MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE,
        )
    )

    results = (await db.execute(stmt)).scalars().all()
    return {"mentors": [str(uid) for uid in results]}


@router.get("/mentees")
async def get_active_mentees_for_user(
    user_id: uuid.UUID = Query(..., description="The mentor user_id to look up"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return mentee user_ids for a user's ACTIVE mentorship connections.

    Logic:
      - Find mentor_profiles.id WHERE user_id = :user_id
      - SELECT mentee_profiles.user_id AS mentee_user_id
        FROM mentorship_connections mc
        JOIN mentee_profiles me ON mc.mentee_id = me.id
        JOIN mentor_profiles mt ON mc.mentor_id = mt.id
        WHERE mt.user_id = :user_id AND mc.status = 'ACTIVE'
    """
    mentor = await db.scalar(
        select(MentorProfile.id).where(MentorProfile.user_id == user_id)
    )

    if mentor is None:
        return {"mentees": []}

    stmt = (
        select(MenteeProfile.user_id)
        .select_from(MentorshipConnection)
        .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
        .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
        .where(
            MentorProfile.user_id == user_id,
            MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE,
        )
    )

    results = (await db.execute(stmt)).scalars().all()
    return {"mentees": [str(uid) for uid in results]}

