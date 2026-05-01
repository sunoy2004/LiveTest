import uuid
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Goal,
    MentorshipConnection,
    Session as MentorshipSession,
    SessionBookingRequest,
    SessionHistory,
    User,
)
from app.utils.display_name import from_email
from app.services.upcoming_sessions_merge import list_merged_upcoming_sessions


def _goal_api_item(row: Goal) -> dict:
    gid = uuid.uuid5(uuid.NAMESPACE_URL, f"{row.user_id}:{row.goal}")
    return {"id": str(gid), "title": row.goal, "status": "ACTIVE"}


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
                func.upper(func.coalesce(MentorshipSession.status, "")) == "SCHEDULED",
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
        """
        Next sessions for this user: ``SCHEDULED`` rows in ``sessions``, plus ``PENDING``
        ``session_booking_requests`` (sorted by start time, capped at ``limit``).

        Scheduled rows may still appear even if ``start_time`` is in the past (legacy data).
        """
        rows = await list_merged_upcoming_sessions(
            self._session, user_id, limit=limit
        )
        out: list[dict] = []
        for row in rows:
            out.append(
                {
                    "session_id": row["session_id"],
                    "booking_request_id": row["booking_request_id"],
                    "start_time": row["start_time"],
                    "meeting_url": row.get("meeting_url"),
                    "status": row["status"],
                    "partner_name": row["partner_name"],
                    "session_credit_cost": row["session_credit_cost"],
                }
            )
        return out

    async def get_goals(self, user_id: uuid.UUID) -> list[dict]:
        stmt = select(Goal).where(Goal.user_id == user_id)
        goals = (await self._session.execute(stmt)).scalars().all()
        return [_goal_api_item(g) for g in goals]

    async def create_goal(self, user_id: uuid.UUID, title: str) -> dict:
        text = title.strip()
        if not text:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Goal title is required")
        if len(text) > 2000:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Goal title is too long")

        row = Goal(user_id=user_id, goal=text)
        self._session.add(row)
        try:
            await self._session.commit()
            await self._session.refresh(row)
        except IntegrityError:
            await self._session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="You already have a goal with this text",
            ) from None

        return _goal_api_item(row)

    async def get_vault(self, user_id: uuid.UUID) -> list[dict]:
        MentorU = aliased(User)
        MenteeU = aliased(User)

        stmt = (
            select(MentorshipSession, SessionHistory, MentorU.email, MenteeU.email)
            .join(SessionHistory, SessionHistory.session_id == MentorshipSession.id)
            .outerjoin(MentorU, MentorshipSession.mentor_user_id == MentorU.user_id)
            .outerjoin(MenteeU, MentorshipSession.mentee_user_id == MenteeU.user_id)
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
            "partner_name": from_email(mentor_email) if sess.mentee_user_id == user_id else from_email(mentee_email)
        } for sess, hist, mentor_email, mentee_email in results]

    async def get_session_booking_request_ledger(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 100,
    ) -> list[dict]:
        """All session booking rows involving this user (mentee or mentor), newest first."""
        MentorU = aliased(User)
        MenteeU = aliased(User)

        stmt = (
            select(SessionBookingRequest, MentorU.email, MenteeU.email)
            .outerjoin(MentorU, SessionBookingRequest.mentor_user_id == MentorU.user_id)
            .outerjoin(MenteeU, SessionBookingRequest.mentee_user_id == MenteeU.user_id)
            .where(
                or_(
                    SessionBookingRequest.mentee_user_id == user_id,
                    SessionBookingRequest.mentor_user_id == user_id,
                )
            )
            .order_by(
                SessionBookingRequest.created_at.desc().nulls_last(),
                SessionBookingRequest.requested_time.desc(),
            )
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        out: list[dict] = []
        for req, mentor_email, mentee_email in rows:
            is_mentee = req.mentee_user_id == user_id
            partner_name = from_email(mentor_email) if is_mentee else from_email(mentee_email)
            st = req.requested_time
            ca = req.created_at
            out.append(
                {
                    "request_id": str(req.id),
                    "status": (req.status or "PENDING").upper(),
                    "requested_time": st.isoformat() if st else None,
                    "created_at": ca.isoformat() if ca else None,
                    "viewer_role": "mentee" if is_mentee else "mentor",
                    "partner_name": partner_name,
                    "mentor_user_id": str(req.mentor_user_id) if req.mentor_user_id else None,
                    "mentee_user_id": str(req.mentee_user_id) if req.mentee_user_id else None,
                }
            )
        return out
