import uuid
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Goal,
    MentorshipConnection,
    Session as MentorshipSession,
    SessionBookingRequest,
    SessionHistory,
)
from app.utils.display_name import label_from_user_id
from app.services.upcoming_sessions_merge import list_merged_upcoming_sessions
from app.utils.profile_display_name import mentee_display_name_map, mentor_display_name_map


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
        stmt = (
            select(MentorshipSession, SessionHistory)
            .join(SessionHistory, SessionHistory.session_id == MentorshipSession.id)
            .where(
                or_(
                    MentorshipSession.mentee_user_id == user_id,
                    MentorshipSession.mentor_user_id == user_id,
                )
            )
            .order_by(MentorshipSession.start_time.desc())
        )
        results = (await self._session.execute(stmt)).all()
        mentor_ids = {s.mentor_user_id for s, _ in results if s.mentor_user_id}
        mentee_ids = {s.mentee_user_id for s, _ in results if s.mentee_user_id}
        mo_map = await mentor_display_name_map(self._session, mentor_ids)
        me_map = await mentee_display_name_map(self._session, mentee_ids)

        def _partner(sess: MentorshipSession) -> str:
            if sess.mentee_user_id == user_id and sess.mentor_user_id:
                return mo_map.get(sess.mentor_user_id) or label_from_user_id(sess.mentor_user_id)
            if sess.mentee_user_id:
                return me_map.get(sess.mentee_user_id) or label_from_user_id(sess.mentee_user_id)
            return "Partner"

        return [
            {
                "session_id": str(sess.id),
                "start_time": sess.start_time,
                "notes": hist.notes or "",
                "rating": hist.rating,
                "partner_name": _partner(sess),
            }
            for sess, hist in results
        ]

    async def get_session_booking_request_ledger(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 100,
    ) -> list[dict]:
        """All session booking rows involving this user (mentee or mentor), newest first."""
        stmt = (
            select(SessionBookingRequest)
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
        rows = (await self._session.execute(stmt)).scalars().all()
        mo_map = await mentor_display_name_map(self._session, {r.mentor_user_id for r in rows if r.mentor_user_id})
        me_map = await mentee_display_name_map(self._session, {r.mentee_user_id for r in rows if r.mentee_user_id})
        out: list[dict] = []
        for req in rows:
            is_mentee = req.mentee_user_id == user_id
            if is_mentee and req.mentor_user_id:
                partner_name = mo_map.get(req.mentor_user_id) or label_from_user_id(req.mentor_user_id)
            elif req.mentee_user_id:
                partner_name = me_map.get(req.mentee_user_id) or label_from_user_id(req.mentee_user_id)
            else:
                partner_name = "Partner"
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
