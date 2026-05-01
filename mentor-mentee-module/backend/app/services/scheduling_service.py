import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models import (
    MentorProfile,
    MentorTier,
    MentorshipConnection,
    SessionBookingRequest,
    TimeSlot,
    User,
)
from app.utils.connection_token import mentoring_connection_token
from app.utils.display_name import from_email


class SchedulingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_available_slots_for_mentor(self, mentor_user_id: uuid.UUID) -> list[dict]:
        stmt = select(TimeSlot).where(
            TimeSlot.mentor_user_id == mentor_user_id,
            TimeSlot.is_booked == False
        ).order_by(TimeSlot.start_time.asc())
        
        slots = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "slot_id": str(s.id),
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "cost_credits": 0,
            }
            for s in slots
        ]

    async def get_my_availability(self, user_id: uuid.UUID) -> list[dict]:
        stmt = select(TimeSlot).where(
            TimeSlot.mentor_user_id == user_id
        ).order_by(TimeSlot.start_time.asc())
        
        slots = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "slot_id": str(s.id),
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "is_booked": s.is_booked,
                "cost_credits": 0,
            }
            for s in slots
        ]

    async def add_availability(self, user_id: uuid.UUID, start_time: datetime, end_time: datetime) -> dict:
        slot = TimeSlot(
            mentor_user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            is_booked=False
        )
        self._session.add(slot)
        await self._session.commit()
        return {"slot_id": str(slot.id), "status": "created"}

    async def delete_availability(self, user_id: uuid.UUID, slot_id: uuid.UUID) -> dict:
        slot = await self._session.scalar(
            select(TimeSlot).where(TimeSlot.id == slot_id, TimeSlot.mentor_user_id == user_id)
        )
        if not slot:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")

        if slot.is_booked:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete a booked slot")

        await self._session.delete(slot)
        await self._session.commit()
        return {"status": "deleted"}

    async def get_connected_mentors(self, mentee_user_id: uuid.UUID) -> list[dict]:
        """Mentors with ACTIVE connection to this mentee (SPA scheduling)."""
        stmt = (
            select(MentorshipConnection, MentorProfile, User)
            .join(MentorProfile, MentorshipConnection.mentor_user_id == MentorProfile.user_id)
            .join(User, MentorProfile.user_id == User.user_id)
            .where(
                MentorshipConnection.mentee_user_id == mentee_user_id,
                MentorshipConnection.status == "ACTIVE",
            )
        )
        rows = (await self._session.execute(stmt)).all()
        out: list[dict] = []
        for conn, mp, mentor_user in rows:
            tier_row = await self._session.scalar(
                select(MentorTier).where(MentorTier.user_id == conn.mentor_user_id)
            )
            tier_txt = (tier_row.tier if tier_row else "PEER").upper()
            conn_token = mentoring_connection_token(conn.mentor_user_id, conn.mentee_user_id)
            out.append(
                {
                    "connection_id": conn_token,
                    "mentor_id": str(conn.mentor_user_id),
                    "mentor_name": from_email(mentor_user.email),
                    "expertise": list(mp.expertise or []),
                    "total_hours": 0,
                    "tier": tier_txt,
                    "session_credit_cost": 0,
                }
            )
        return sorted(out, key=lambda x: x["mentor_name"])

    async def verify_mentorship_slot(
        self,
        *,
        mentee_user_id: uuid.UUID,
        connection_token: str,
        mentor_user_id: uuid.UUID,
    ) -> MentorshipConnection:
        stmt = select(MentorshipConnection).where(
            MentorshipConnection.mentee_user_id == mentee_user_id,
            MentorshipConnection.mentor_user_id == mentor_user_id,
            MentorshipConnection.status == "ACTIVE",
        )
        conn = await self._session.scalar(stmt)
        if conn is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
        if mentoring_connection_token(conn.mentor_user_id, conn.mentee_user_id) != connection_token:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid connection")
        return conn

    async def get_available_slots_for_mentorship(
        self,
        *,
        mentee_user_id: uuid.UUID,
        connection_token: str,
        mentor_user_id: uuid.UUID,
    ) -> list[dict]:
        await self.verify_mentorship_slot(
            mentee_user_id=mentee_user_id,
            connection_token=connection_token,
            mentor_user_id=mentor_user_id,
        )
        return await self.get_available_slots_for_mentor(mentor_user_id)

    async def book_session_simple(
        self,
        *,
        mentee_user_id: uuid.UUID,
        connection_id: str,
        slot_id: uuid.UUID,
    ) -> dict:
        stmt = select(MentorshipConnection).where(
            MentorshipConnection.mentee_user_id == mentee_user_id,
            MentorshipConnection.status == "ACTIVE",
        )
        conns = (await self._session.execute(stmt)).scalars().all()
        match: MentorshipConnection | None = None
        for c in conns:
            if mentoring_connection_token(c.mentor_user_id, c.mentee_user_id) == connection_id:
                match = c
                break
        if match is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")

        slot = await self._session.scalar(
            select(TimeSlot).where(
                TimeSlot.id == slot_id,
                TimeSlot.mentor_user_id == match.mentor_user_id,
            )
        )
        if slot is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")
        if slot.is_booked:
            raise HTTPException(status.HTTP_409_CONFLICT, "Slot is no longer available")

        booking = SessionBookingRequest(
            mentor_user_id=match.mentor_user_id,
            mentee_user_id=match.mentee_user_id,
            requested_time=slot.start_time,
            status="PENDING",
        )
        self._session.add(booking)
        await self._session.commit()
        await self._session.refresh(booking)

        st = booking.requested_time
        start_iso = st.isoformat() if st else ""
        return {
            "request_id": str(booking.id),
            "session_id": None,
            "status": "PENDING_APPROVAL",
            "meeting_url": None,
            "start_time": start_iso,
        }
