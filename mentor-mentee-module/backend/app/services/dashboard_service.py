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
        # Check if user has ANY mentorship participation (mentee or mentor)
        # This is a lightweight check to avoid 0-stat displays for non-participants.
        participant = await self._session.scalar(
            select(MentorshipConnection.id).where(
                or_(
                    MentorshipConnection.mentee_id == user_id,
                    MentorshipConnection.mentor_id == user_id
                )
            ).limit(1)
        )
        if not participant:
            return {
                "active_partners": 0,
                "hours_total": 0.0,
                "hours_this_week": 0.0,
                "sessions_completed": 0,
                "active_sessions": 0,
            }

        conn_ids_stmt = select(MentorshipConnection.id).where(
            MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE,
            or_(
                MentorshipConnection.mentee_id == user_id,
                MentorshipConnection.mentor_id == user_id
            )
        )
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
        from sqlalchemy.orm import aliased
        MenteeP = aliased(MenteeProfile)
        MentorP = aliased(MentorProfile)

        stmt = (
            select(
                MentorshipSession, 
                TimeSlot,
                MentorshipConnection,
                MenteeP.first_name.label("mentee_fn"),
                MenteeP.last_name.label("mentee_ln"),
                MentorP.first_name.label("mentor_fn"),
                MentorP.last_name.label("mentor_ln")
            )
            .join(TimeSlot, MentorshipSession.slot_id == TimeSlot.id)
            .join(MentorshipConnection, MentorshipSession.connection_id == MentorshipConnection.id)
            .outerjoin(MenteeP, MentorshipConnection.mentee_id == MenteeP.user_id)
            .outerjoin(MentorP, MentorshipConnection.mentor_id == MentorP.user_id)
            .where(
                MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE,
                or_(
                    MentorshipConnection.mentee_id == user_id,
                    MentorshipConnection.mentor_id == user_id
                ),
                MentorshipSession.status == SessionStatus.SCHEDULED,
                TimeSlot.start_time > datetime.now(timezone.utc)
            )
            .order_by(TimeSlot.start_time.asc())
            .limit(limit)
        )

        rows = (await self._session.execute(stmt)).all()
        
        out = []
        for s, slot, conn, me_fn, me_ln, mo_fn, mo_ln in rows:
            # Determine partner name
            if conn.mentee_id == user_id:
                partner_name = f"{mo_fn or ''} {mo_ln or ''}".strip() or "Mentor"
            else:
                partner_name = f"{me_fn or ''} {me_ln or ''}".strip() or "Mentee"

            out.append({
                "session_id": str(s.id),
                "start_time": slot.start_time,
                "status": s.status,
                "connection_id": str(s.connection_id),
                "partner_name": partner_name
            })
        return out

    async def get_goals(self, user_id: uuid.UUID) -> list[dict]:
        from app.models import Goal
        
        stmt = select(Goal).join(MentorshipConnection).where(
            MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE,
            or_(
                MentorshipConnection.mentee_id == user_id,
                MentorshipConnection.mentor_id == user_id
            )
        )
        goals = (await self._session.execute(stmt)).scalars().all()
        return [{"id": str(g.id), "title": g.title, "status": g.status} for g in goals]

    async def get_vault(self, user_id: uuid.UUID) -> list[dict]:
        from app.models import SessionHistory
        from sqlalchemy.orm import aliased
        MenteeP = aliased(MenteeProfile)
        MentorP = aliased(MentorProfile)
        
        stmt = (
            select(
                MentorshipSession, 
                SessionHistory, 
                TimeSlot,
                MentorshipConnection,
                MenteeP.first_name.label("mentee_fn"),
                MenteeP.last_name.label("mentee_ln"),
                MentorP.first_name.label("mentor_fn"),
                MentorP.last_name.label("mentor_ln")
            )
            .join(MentorshipConnection, MentorshipSession.connection_id == MentorshipConnection.id)
            .join(SessionHistory, SessionHistory.session_id == MentorshipSession.id)
            .join(TimeSlot, MentorshipSession.slot_id == TimeSlot.id)
            .outerjoin(MenteeP, MentorshipConnection.mentee_id == MenteeP.user_id)
            .outerjoin(MentorP, MentorshipConnection.mentor_id == MentorP.user_id)
            .where(
                or_(
                    MentorshipConnection.mentee_id == user_id,
                    MentorshipConnection.mentor_id == user_id
                )
            )
            .order_by(TimeSlot.start_time.desc())
        )
        results = (await self._session.execute(stmt)).all()
        return [{
            "session_id": str(sess.id),
            "start_time": slot.start_time,
            "notes": hist.notes_data or {},
            "mentor_rating": hist.mentor_rating,
            "mentee_rating": hist.mentee_rating,
            "partner_name": (f"{mo_fn or ''} {mo_ln or ''}".strip() or "Mentor") if conn.mentee_id == user_id else (f"{me_fn or ''} {me_ln or ''}".strip() or "Mentee")
        } for sess, hist, slot, conn, me_fn, me_ln, mo_fn, mo_ln in results]
