import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    MenteeProfile,
    MentorProfile,
    MentorshipConnection,
    MentorshipConnectionStatus,
    Session as MentorshipSession,
    SessionStatus,
    TimeSlot
)

class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_stats(self, user_id: uuid.UUID) -> dict:
        # Identify profile IDs
        mentee_id = await self._session.scalar(
            select(MenteeProfile.id).where(MenteeProfile.user_id == user_id)
        )
        mentor_id = await self._session.scalar(
            select(MentorProfile.id).where(MentorProfile.user_id == user_id)
        )

        if not mentee_id and not mentor_id:
            return {
                "active_partners": 0,
                "hours_total": 0.0,
                "hours_this_week": 0.0,
                "sessions_completed": 0,
                "active_sessions": 0,
            }

        conn_ids_stmt = select(MentorshipConnection.id).where(
            MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE
        )
        conditions = []
        if mentee_id:
            conditions.append(MentorshipConnection.mentee_id == mentee_id)
        if mentor_id:
            conditions.append(MentorshipConnection.mentor_id == mentor_id)
        
        conn_ids_stmt = conn_ids_stmt.where(or_(*conditions))
        conn_ids = (await self._session.execute(conn_ids_stmt)).scalars().all()

        if not conn_ids:
            return {
                "active_partners": 0,
                "hours_total": 0.0,
                "hours_this_week": 0.0,
                "sessions_completed": 0,
                "active_sessions": 0,
            }

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # Sessions stats
        completed_stmt = select(MentorshipSession, TimeSlot).join(
            TimeSlot, TimeSlot.id == MentorshipSession.slot_id
        ).where(
            MentorshipSession.connection_id.in_(conn_ids),
            MentorshipSession.status == SessionStatus.COMPLETED
        )
        
        completed_rows = (await self._session.execute(completed_stmt)).all()
        
        hours_total = 0.0
        hours_week = 0.0
        for sess, slot in completed_rows:
            duration = (slot.end_time - slot.start_time).total_seconds() / 3600.0
            hours_total += duration
            if slot.start_time >= week_ago:
                hours_week += duration

        active_ct = await self._session.scalar(
            select(func.count(MentorshipSession.id)).where(
                MentorshipSession.connection_id.in_(conn_ids),
                MentorshipSession.status == SessionStatus.SCHEDULED
            )
        )

        return {
            "active_partners": len(conn_ids),
            "hours_total": hours_total,
            "hours_this_week": hours_week,
            "sessions_completed": len(completed_rows),
            "active_sessions": active_ct or 0,
        }

    async def get_upcoming_sessions(self, user_id: uuid.UUID, limit: int = 5) -> list[dict]:
        mentee_id = await self._session.scalar(
            select(MenteeProfile.id).where(MenteeProfile.user_id == user_id)
        )
        mentor_id = await self._session.scalar(
            select(MentorProfile.id).where(MentorProfile.user_id == user_id)
        )

        if not mentee_id and not mentor_id:
            return []

        conditions = []
        if mentee_id:
            conditions.append(MentorshipConnection.mentee_id == mentee_id)
        if mentor_id:
            conditions.append(MentorshipConnection.mentor_id == mentor_id)

        conn_ids_stmt = select(MentorshipConnection.id).where(
            or_(*conditions),
            MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE
        )
        conn_ids = (await self._session.execute(conn_ids_stmt)).scalars().all()

        if not conn_ids:
            return []

        now = datetime.now(timezone.utc)
        stmt = (
            select(MentorshipSession, TimeSlot)
            .join(TimeSlot, MentorshipSession.slot_id == TimeSlot.id)
            .where(
                MentorshipSession.connection_id.in_(conn_ids),
                MentorshipSession.status == SessionStatus.SCHEDULED,
                TimeSlot.start_time > now
            )
            .order_by(TimeSlot.start_time.asc())
            .limit(limit)
        )

        rows = (await self._session.execute(stmt)).all()
        
        out = []
        for s, slot in rows:
            out.append({
                "session_id": str(s.id),
                "start_time": slot.start_time,
                "status": s.status,
                "connection_id": str(s.connection_id)
            })
        return out

    async def get_goals(self, user_id: uuid.UUID) -> list[dict]:
        from app.models import Goal
        mentee_id = await self._session.scalar(select(MenteeProfile.id).where(MenteeProfile.user_id == user_id))
        mentor_id = await self._session.scalar(select(MentorProfile.id).where(MentorProfile.user_id == user_id))
        
        conditions = []
        if mentee_id: conditions.append(MentorshipConnection.mentee_id == mentee_id)
        if mentor_id: conditions.append(MentorshipConnection.mentor_id == mentor_id)
        
        if not conditions: return []
        
        stmt = select(Goal).join(MentorshipConnection).where(
            or_(*conditions),
            MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE
        )
        goals = (await self._session.execute(stmt)).scalars().all()
        return [{"id": str(g.id), "title": g.title, "status": g.status} for g in goals]

    async def get_vault(self, user_id: uuid.UUID) -> list[dict]:
        from app.models import SessionHistory
        mentee_id = await self._session.scalar(select(MenteeProfile.id).where(MenteeProfile.user_id == user_id))
        mentor_id = await self._session.scalar(select(MentorProfile.id).where(MentorProfile.user_id == user_id))
        
        conditions = []
        if mentee_id: conditions.append(MentorshipConnection.mentee_id == mentee_id)
        if mentor_id: conditions.append(MentorshipConnection.mentor_id == mentor_id)
        
        if not conditions: return []
        
        stmt = (
            select(MentorshipSession, SessionHistory, TimeSlot)
            .join(MentorshipConnection, MentorshipSession.connection_id == MentorshipConnection.id)
            .join(SessionHistory, SessionHistory.session_id == MentorshipSession.id)
            .join(TimeSlot, MentorshipSession.slot_id == TimeSlot.id)
            .where(or_(*conditions))
            .order_by(TimeSlot.start_time.desc())
        )
        results = (await self._session.execute(stmt)).all()
        return [{
            "session_id": str(sess.id),
            "start_time": slot.start_time,
            "notes": hist.notes_data or {},
            "mentor_rating": hist.mentor_rating,
            "mentee_rating": hist.mentee_rating,
        } for sess, hist, slot in results]
