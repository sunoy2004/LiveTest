"""Merge scheduled sessions and pending booking requests for dashboard / sessions APIs."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session as MentorshipSession
from app.models import SessionBookingRequest
from app.services.book_mentor_session_credits import resolve_default_book_session_credits
from app.models import MentorTier
from app.utils.display_name import label_from_user_id


def _dt_key(dt: datetime | None) -> float:
    if dt is None:
        return float("inf")
    return dt.timestamp()


async def list_merged_upcoming_sessions(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
) -> list[dict]:
    """
    Scheduled mentorship sessions plus pending session_booking_requests for this user.

    Each item includes dashboard-facing fields; callers may add or strip keys.
    """
    tier_def = await session.get(MentorTier, "PEER")
    tier_fallback = int(tier_def.session_credit_cost) if tier_def else 0
    cost = await resolve_default_book_session_credits(tier_fallback)

    cap = max(limit * 4, limit + 10)

    stmt_sched = (
        select(MentorshipSession)
        .where(
            or_(
                MentorshipSession.mentee_user_id == user_id,
                MentorshipSession.mentor_user_id == user_id,
            ),
            func.upper(func.coalesce(MentorshipSession.status, "")) == "SCHEDULED",
        )
        .order_by(
            func.coalesce(
                MentorshipSession.start_time,
                MentorshipSession.created_at,
            ).asc().nulls_last()
        )
        .limit(cap)
    )

    stmt_pending = (
        select(SessionBookingRequest)
        .where(
            or_(
                SessionBookingRequest.mentee_user_id == user_id,
                SessionBookingRequest.mentor_user_id == user_id,
            ),
            func.upper(func.coalesce(SessionBookingRequest.status, "")) == "PENDING",
        )
        .order_by(
            func.coalesce(
                SessionBookingRequest.requested_time,
                SessionBookingRequest.created_at,
            ).asc().nulls_last()
        )
        .limit(cap)
    )

    rows_s = (await session.execute(stmt_sched)).scalars().all()
    rows_p = (await session.execute(stmt_pending)).scalars().all()

    merged: list[tuple[float, dict]] = []

    for s in rows_s:
        if s.mentee_user_id == user_id:
            partner_name = label_from_user_id(s.mentor_user_id)
        else:
            partner_name = label_from_user_id(s.mentee_user_id)

        display_start = s.start_time or s.created_at
        st_iso = display_start.isoformat() if display_start else ""
        end_iso = s.end_time.isoformat() if s.end_time else None

        merged.append(
            (
                _dt_key(display_start),
                {
                    "session_id": str(s.id),
                    "booking_request_id": None,
                    "start_time": st_iso,
                    "end_time": end_iso,
                    "meeting_url": None,
                    "status": (s.status or "SCHEDULED").strip() or "SCHEDULED",
                    "partner_name": partner_name,
                    "session_credit_cost": cost,
                    "mentor_user_id": str(s.mentor_user_id),
                    "mentee_user_id": str(s.mentee_user_id),
                },
            )
        )

    for req in rows_p:
        if req.mentee_user_id == user_id:
            partner_name = label_from_user_id(req.mentor_user_id)
        else:
            partner_name = label_from_user_id(req.mentee_user_id)

        display_start = req.requested_time or req.created_at
        st_iso = display_start.isoformat() if display_start else ""
        end_dt = (
            (req.requested_time + timedelta(hours=1))
            if req.requested_time
            else None
        )
        end_iso = end_dt.isoformat() if end_dt else None

        merged.append(
            (
                _dt_key(display_start),
                {
                    "session_id": None,
                    "booking_request_id": str(req.id),
                    "start_time": st_iso,
                    "end_time": end_iso,
                    "meeting_url": None,
                    "status": "PENDING",
                    "partner_name": partner_name,
                    "session_credit_cost": cost,
                    "mentor_user_id": str(req.mentor_user_id) if req.mentor_user_id else "",
                    "mentee_user_id": str(req.mentee_user_id) if req.mentee_user_id else "",
                },
            )
        )

    merged.sort(key=lambda x: x[0])
    out = [payload for _, payload in merged[:limit]]

    return out
