import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.models import MentorProfile, MenteeProfile, MentorshipConnection

router = APIRouter()

@router.get("/matchmaking-snapshot")
async def get_matchmaking_snapshot(
    db: AsyncSession = Depends(get_db)
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
