import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MenteeProfile
from app.models import MentorTier
from app.models import MentorshipConnection
from app.models import Session as MentorshipSession
from app.models import SessionBookingRequest
from app.models import SessionHistory
from app.models import TimeSlot
from app.services.book_mentor_session_credits import resolve_default_book_session_credits
from app.services.gamification_transactions import (
    deduct_book_mentor_session_credits,
    fetch_wallet_balance_from_gamification,
)
from app.services.upcoming_sessions_merge import list_merged_upcoming_sessions
from app.utils.connection_token import mentoring_connection_token
from app.utils.display_name import label_from_user_id
from app.utils.profile_display_name import mentee_display_name_map


class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_upcoming_sessions(self, user_id: uuid.UUID) -> list[dict]:
        """Scheduled sessions and pending booking requests (same merge as dashboard)."""
        rows = await list_merged_upcoming_sessions(self._session, user_id, limit=100)
        out: list[dict] = []
        for r in rows:
            sid = r["session_id"]
            out.append(
                {
                    "session_id": sid,
                    "booking_request_id": r["booking_request_id"],
                    "start_time": r["start_time"],
                    "end_time": r["end_time"],
                    "status": r["status"],
                    "mentor_user_id": r["mentor_user_id"],
                    "mentee_user_id": r["mentee_user_id"],
                }
            )
        return out

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
        mentee_ids = {r.mentee_user_id for r in rows if r.mentee_user_id}
        mentee_names = await mentee_display_name_map(self._session, mentee_ids)
        tier_def = await self._session.get(MentorTier, "PEER")
        tier_fallback = int(tier_def.session_credit_cost) if tier_def else 0
        default_booking_credits = await resolve_default_book_session_credits(tier_fallback)
        out: list[dict] = []
        for req in rows:
            if req.mentee_user_id:
                mentee_name = mentee_names.get(req.mentee_user_id) or label_from_user_id(req.mentee_user_id)
            else:
                mentee_name = "Mentee"
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
                    "agreed_cost": default_booking_credits,
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

        tier_def = await self._session.get(MentorTier, "PEER")
        tier_fallback = int(tier_def.session_credit_cost) if tier_def else 0
        credit_amount = await resolve_default_book_session_credits(tier_fallback)
        if credit_amount < 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Session booking credit amount is not configured",
            )

        mentee_id = req.mentee_user_id
        if mentee_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking has no mentee")

        end_dt = req.requested_time + timedelta(hours=1)
        if slot and slot.end_time:
            end_dt = slot.end_time

        # Do not query mentorship_connections.connection_id via raw SQL: many DBs use a
        # composite PK only (no connection_id column). A failed SELECT aborts the whole
        # transaction and the next INSERT raises InFailedSQLTransactionError.
        active_conn = await self._session.scalar(
            select(MentorshipConnection).where(
                MentorshipConnection.mentor_user_id == req.mentor_user_id,
                MentorshipConnection.mentee_user_id == req.mentee_user_id,
                func.upper(func.trim(func.coalesce(MentorshipConnection.status, ""))) == "ACTIVE",
            )
        )
        if active_conn is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="No active mentorship connection for this booking",
            )
        # sessions.connection_id is optional (nullable); composite-key schemas have no UUID on connections.
        connection_uuid: uuid.UUID | None = None

        new_sess = MentorshipSession(
            mentor_user_id=req.mentor_user_id,
            mentee_user_id=req.mentee_user_id,
            start_time=req.requested_time,
            end_time=end_dt,
            status="SCHEDULED",
            connection_id=connection_uuid,
            slot_id=slot.id if slot else None,
            session_credit_cost=credit_amount,
        )
        self._session.add(new_sess)
        req.status = "APPROVED"
        if slot:
            slot.is_booked = True

        # Validate DB constraints before charging gamification (deduct is not rolled back with SQL).
        try:
            await self._session.flush()
        except IntegrityError as e:
            await self._session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Could not create the session row. Apply mentoring Alembic migrations (e.g. 005_sessions_align, 006_sessions_conn_slot) so sessions has required columns.",
            ) from e

        idempotency_key = f"mentoring_booking_accept:{request_id}"
        try:
            balance_after = await deduct_book_mentor_session_credits(
                mentee_user_id=mentee_id,
                amount=credit_amount,
                idempotency_key=idempotency_key,
            )
        except HTTPException:
            await self._session.rollback()
            raise

        # Re-read wallet from gamification so mentoring cache matches the ledger (deduct response
        # shape can vary; this also confirms the spend was committed before we cache locally).
        verified = await fetch_wallet_balance_from_gamification(mentee_id)
        if verified is not None:
            balance_after = verified

        profile = await self._session.get(MenteeProfile, mentee_id)
        if profile is not None:
            profile.cached_credit_score = balance_after

        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Could not finalize the session. Check mentoring DB schema and migrations.",
            ) from e
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
