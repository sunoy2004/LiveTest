import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session as MentorshipSession
from app.models import SessionBookingRequest
from app.models import SessionHistory
from app.models import TimeSlot
from app.models import User
from app.utils.connection_token import mentoring_connection_token
from app.utils.display_name import from_email


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
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "status": s.status,
                "mentor_user_id": str(s.mentor_user_id),
                "mentee_user_id": str(s.mentee_user_id),
            }
            for s in sessions
        ]

    async def list_incoming_booking_requests(self, mentor_user_id: uuid.UUID) -> list[dict]:
        stmt = (
            select(SessionBookingRequest)
            .where(
                SessionBookingRequest.mentor_user_id == mentor_user_id,
                SessionBookingRequest.status == "PENDING",
            )
            .order_by(SessionBookingRequest.requested_time.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        out: list[dict] = []
        for req in rows:
            mentee_u = await self._session.get(User, req.mentee_user_id) if req.mentee_user_id else None
            mentee_name = from_email(mentee_u.email if mentee_u else None) or "Mentee"
            conn_id = mentoring_connection_token(req.mentor_user_id, req.mentee_user_id)
            slot_row = await self._session.scalar(
                select(TimeSlot).where(
                    TimeSlot.mentor_user_id == req.mentor_user_id,
                    TimeSlot.start_time == req.requested_time,
                )
            )
            slot_id_str = str(slot_row.id) if slot_row else ""
            end_iso = (
                slot_row.end_time.isoformat()
                if slot_row and slot_row.end_time
                else (req.requested_time.isoformat() if req.requested_time else "")
            )
            out.append(
                {
                    "request_id": str(req.id),
                    "connection_id": conn_id,
                    "slot_id": slot_id_str,
                    "start_time": req.requested_time.isoformat() if req.requested_time else "",
                    "end_time": end_iso,
                    "agreed_cost": 0,
                    "mentee_name": mentee_name,
                    "status": req.status or "PENDING",
                }
            )
        return out

    async def accept_booking_request(self, mentor_user_id: uuid.UUID, request_id: uuid.UUID) -> dict:
        req = await self._session.get(SessionBookingRequest, request_id)
        if req is None or req.mentor_user_id != mentor_user_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
        if (req.status or "PENDING") != "PENDING":
            raise HTTPException(status.HTTP_409_CONFLICT, "Request already processed")

        slot = await self._session.scalar(
            select(TimeSlot).where(
                TimeSlot.mentor_user_id == req.mentor_user_id,
                TimeSlot.start_time == req.requested_time,
            )
        )
        if slot and slot.is_booked:
            raise HTTPException(status.HTTP_409_CONFLICT, "Slot is no longer available")

        end_dt = req.requested_time + timedelta(hours=1)
        if slot and slot.end_time:
            end_dt = slot.end_time

        new_sess = MentorshipSession(
            mentor_user_id=req.mentor_user_id,
            mentee_user_id=req.mentee_user_id,
            start_time=req.requested_time,
            end_time=end_dt,
            status="SCHEDULED",
        )
        self._session.add(new_sess)
        req.status = "APPROVED"
        if slot:
            slot.is_booked = True
        await self._session.commit()
        await self._session.refresh(new_sess)
        st = new_sess.start_time
        return {
            "session_id": str(new_sess.id),
            "status": "SCHEDULED",
            "meeting_url": None,
            "start_time": st.isoformat() if st else "",
        }

    async def reject_booking_request(self, mentor_user_id: uuid.UUID, request_id: uuid.UUID) -> None:
        req = await self._session.get(SessionBookingRequest, request_id)
        if req is None or req.mentor_user_id != mentor_user_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
        if (req.status or "PENDING") != "PENDING":
            raise HTTPException(status.HTTP_409_CONFLICT, "Request already processed")
        req.status = "REJECTED"
        await self._session.commit()

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
