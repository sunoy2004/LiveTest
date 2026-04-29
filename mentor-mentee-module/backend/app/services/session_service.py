import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models import Session, SessionStatus, TimeSlot, MentorProfile, MentorshipConnection, SessionHistory

class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_upcoming_sessions(self, user_id: uuid.UUID) -> list[dict]:
        # This logic is similar to DashboardService but more detailed
        mentor_id = await self._session.scalar(select(MentorProfile.id).where(MentorProfile.user_id == user_id))
        
        stmt = select(Session).join(MentorshipConnection).join(TimeSlot)
        if mentor_id:
            stmt = stmt.where(MentorshipConnection.mentor_id == mentor_id)
        else:
            from app.models import MenteeProfile
            mentee_id = await self._session.scalar(select(MenteeProfile.id).where(MenteeProfile.user_id == user_id))
            if not mentee_id: return []
            stmt = stmt.where(MentorshipConnection.mentee_id == mentee_id)
            
        stmt = stmt.where(Session.status == SessionStatus.SCHEDULED).order_by(TimeSlot.start_time.asc())
        sessions = (await self._session.execute(stmt)).scalars().all()
        
        return [
            {
                "session_id": str(s.id),
                "start_time": s.slot.start_time,
                "status": s.status,
                "connection_id": str(s.connection_id)
            }
            for s in sessions
        ]

    async def create_session_history(self, user_id: uuid.UUID, session_id: uuid.UUID, notes: dict) -> dict:
        sess = await self._session.get(Session, session_id)
        if not sess:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
            
        # Check if user is part of the session
        mentor = await self._session.scalar(select(MentorProfile).where(MentorProfile.user_id == user_id))
        if not mentor or sess.connection.mentor_id != mentor.id:
             # Check if mentee
             from app.models import MenteeProfile
             mentee = await self._session.scalar(select(MenteeProfile).where(MenteeProfile.user_id == user_id))
             if not mentee or sess.connection.mentee_id != mentee.id:
                 raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this session")

        history = SessionHistory(
            session_id=session_id,
            notes_data=notes.get("notes"),
            mentor_rating=notes.get("mentor_rating"),
            mentee_rating=notes.get("mentee_rating")
        )
        self._session.add(history)
        sess.status = SessionStatus.COMPLETED
        await self._session.commit()
        return {"status": "history_created"}
