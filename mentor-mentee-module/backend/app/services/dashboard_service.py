import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    MenteeProfile,
    MentorProfile,
    MentorshipConnection,
    Session as MentorshipSession,
    TimeSlot,
    Goal,
    SessionHistory
)

class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_stats(self, user_id: uuid.UUID) -> dict:
        # Check for active connections using composite PK structure
        stmt = select(MentorshipConnection).where(
            or_(
                MentorshipConnection.mentee_user_id == user_id,
                MentorshipConnection.mentor_user_id == user_id
            ),
            MentorshipConnection.status == "ACTIVE"
        )
        active_conns = (await self._session.execute(stmt)).scalars().all()
        
        if not active_conns:
            return {
                "active_partners": 0,
                "hours_total": 0.0,
                "hours_this_week": 0.0,
                "sessions_completed": 0,
                "active_sessions": 0,
            }

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # Query sessions directly linked to user
        completed_stmt = select(MentorshipSession).where(
            or_(
                MentorshipSession.mentee_user_id == user_id,
                MentorshipSession.mentor_user_id == user_id
            ),
            MentorshipSession.status == "COMPLETED"
        )
        completed_sessions = (await self._session.execute(completed_stmt)).scalars().all()
        
        hours_total = 0.0
        hours_week = 0.0
        for sess in completed_sessions:
            if sess.start_time and sess.end_time:
                duration = (sess.end_time - sess.start_time).total_seconds() / 3600.0
                hours_total += duration
                if sess.start_time >= week_ago:
                    hours_week += duration

        active_ct = await self._session.scalar(
            select(func.count(MentorshipSession.id)).where(
                or_(
                    MentorshipSession.mentee_user_id == user_id,
                    MentorshipSession.mentor_user_id == user_id
                ),
                MentorshipSession.status == "SCHEDULED"
            )
        )

        return {
            "active_partners": len(active_conns),
            "hours_total": round(hours_total, 1),
            "hours_this_week": round(hours_week, 1),
            "sessions_completed": len(completed_sessions),
            "active_sessions": active_ct or 0,
        }

    async def get_upcoming_sessions(self, user_id: uuid.UUID, limit: int = 5) -> list[dict]:
        from sqlalchemy.orm import aliased
        MenteeP = aliased(MenteeProfile)
        MentorP = aliased(MentorProfile)

        stmt = (
            select(
                MentorshipSession, 
                MenteeP.first_name.label("mentee_fn"),
                MenteeP.last_name.label("mentee_ln"),
                MentorP.first_name.label("mentor_fn"),
                MentorP.last_name.label("mentor_ln")
            )
            .outerjoin(MenteeP, MentorshipSession.mentee_user_id == MenteeP.user_id)
            .outerjoin(MentorP, MentorshipSession.mentor_user_id == MentorP.user_id)
            .where(
                or_(
                    MentorshipSession.mentee_user_id == user_id,
                    MentorshipSession.mentor_user_id == user_id
                ),
                MentorshipSession.status == "SCHEDULED",
                MentorshipSession.start_time > datetime.now(timezone.utc)
            )
            .order_by(MentorshipSession.start_time.asc())
            .limit(limit)
        )

        rows = (await self._session.execute(stmt)).all()
        
        out = []
        for s, me_fn, me_ln, mo_fn, mo_ln in rows:
            if s.mentee_user_id == user_id:
                partner_name = f"{mo_fn or ''} {mo_ln or ''}".strip() or "Mentor"
            else:
                partner_name = f"{me_fn or ''} {me_ln or ''}".strip() or "Mentee"

            out.append({
                "session_id": str(s.id),
                "start_time": s.start_time,
                "status": s.status,
                "partner_name": partner_name
            })
        return out

    async def get_goals(self, user_id: uuid.UUID) -> list[dict]:
        stmt = select(Goal).where(Goal.user_id == user_id)
        goals = (await self._session.execute(stmt)).scalars().all()
        return [{"id": str(g.user_id), "title": g.goal, "status": "ACTIVE"} for g in goals]

    async def get_vault(self, user_id: uuid.UUID) -> list[dict]:
        from sqlalchemy.orm import aliased
        MenteeP = aliased(MenteeProfile)
        MentorP = aliased(MentorProfile)
        
        stmt = (
            select(
                MentorshipSession, 
                SessionHistory, 
                MenteeP.first_name.label("mentee_fn"),
                MenteeP.last_name.label("mentee_ln"),
                MentorP.first_name.label("mentor_fn"),
                MentorP.last_name.label("mentor_ln")
            )
            .join(SessionHistory, SessionHistory.session_id == MentorshipSession.id)
            .outerjoin(MenteeP, MentorshipSession.mentee_user_id == MenteeP.user_id)
            .outerjoin(MentorP, MentorshipSession.mentor_user_id == MentorP.user_id)
            .where(
                or_(
                    MentorshipSession.mentee_user_id == user_id,
                    MentorshipSession.mentor_user_id == user_id
                )
            )
            .order_by(MentorshipSession.start_time.desc())
        )
        results = (await self._session.execute(stmt)).all()
        return [{
            "session_id": str(sess.id),
            "start_time": sess.start_time,
            "notes": hist.notes or "",
            "rating": hist.rating,
            "partner_name": (f"{mo_fn or ''} {mo_ln or ''}".strip() or "Mentor") if sess.mentee_user_id == user_id else (f"{me_fn or ''} {me_ln or ''}".strip() or "Mentee")
        } for sess, hist, me_fn, me_ln, mo_fn, mo_ln in results]
