import uuid
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models import MentorProfile, TimeSlot, MenteeProfile, MentorshipConnection

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
                "start_time": s.start_time,
                "end_time": s.end_time,
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
                "start_time": s.start_time,
                "end_time": s.end_time,
                "is_booked": s.is_booked
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
