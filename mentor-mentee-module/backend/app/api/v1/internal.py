import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.models import MentorProfile, MenteeProfile, MentorshipConnection

router = APIRouter()

_INTERNAL_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")


async def require_internal_token(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
) -> None:
    if not _INTERNAL_TOKEN or x_internal_token != _INTERNAL_TOKEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid internal token")


@router.get("/matchmaking-snapshot")
async def get_matchmaking_snapshot(
    _: None = Depends(require_internal_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Internal endpoint for AI service to fetch all data for re-indexing.
    """
    # Fetch all mentors
    mentors_stmt = select(MentorProfile)
    mentors = (await db.execute(mentors_stmt)).scalars().all()
    
    # Fetch all mentees
    mentees_stmt = select(MenteeProfile)
    mentees = (await db.execute(mentees_stmt)).scalars().all()
    
    # Fetch all connections
    conn_stmt = select(MentorshipConnection).where(MentorshipConnection.status == "ACTIVE")
    connections = (await db.execute(conn_stmt)).scalars().all()
    
    return {
        "mentors": [
            {
                "user_id": str(m.user_id),
                "expertise": m.expertise or [],
                "bio": m.bio,
                "experience_years": m.experience_years
            }
            for m in mentors
        ],
        "mentees": [
            {
                "user_id": str(m.user_id),
                "learning_goals": m.learning_goals or [],
                "education_level": m.education_level
            }
            for m in mentees
        ],
        "connections": [
            {
                "mentor_id": str(c.mentor_user_id),
                "mentee_id": str(c.mentee_user_id)
            }
            for c in connections
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
