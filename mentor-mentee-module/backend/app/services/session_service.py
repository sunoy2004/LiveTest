import uuid
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models import Session as MentorshipSession, TimeSlot, MentorProfile, MentorshipConnection, SessionHistory, MenteeProfile

class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_upcoming_sessions(self, user_id: uuid.UUID) -> list[dict]:
        # Sessions now directly link to mentor_user_id and mentee_user_id
        stmt = (
            select(MentorshipSession)
            .where(
                or_(
                    MentorshipSession.mentor_user_id == user_id,
                    MentorshipSession.mentee_user_id == user_id
                ),
                MentorshipSession.status == "SCHEDULED"
            )
            .order_by(MentorshipSession.start_time.asc())
        )
        sessions = (await self._session.execute(stmt)).scalars().all()
        
        return [
            {
                "session_id": str(s.id),
                "start_time": s.start_time,
                "end_time": s.end_time,
                "status": s.status,
                "mentor_user_id": str(s.mentor_user_id),
                "mentee_user_id": str(s.mentee_user_id),
            }
            for s in sessions
        ]

    async def create_session_history(self, user_id: uuid.UUID, session_id: uuid.UUID, notes: dict) -> dict:
        sess = await self._session.get(MentorshipSession, session_id)
        if not sess:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
            
        # Check if user is part of the session
        if user_id not in [sess.mentor_user_id, sess.mentee_user_id]:
             raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this session")

        # SessionHistory in new schema uses session_id as PK (or part of it)
        # And columns are: session_id, notes, rating
        history = SessionHistory(
            session_id=session_id,
            notes=notes.get("notes"),
            rating=notes.get("rating")
        )
        self._session.add(history)
        sess.status = "COMPLETED"
        await self._session.commit()
        return {"status": "history_created"}
