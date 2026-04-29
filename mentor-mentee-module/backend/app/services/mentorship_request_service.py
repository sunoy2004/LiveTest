import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import aliased
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.publisher import publish_event
from app.models import (
    MenteeProfile,
    MentorProfile,
    MentorshipConnection,
    MentorshipRequest,
)
from app.models.enums import (
    GuardianConsentStatus,
    MentorshipConnectionStatus,
    MentorshipRequestStatus,
)
from app.schemas.request import MentorshipRequestCreate, MentorshipRequestStatusUpdate

TOPIC_MENTORING_CONNECTIONS = "mentoring.connections.events"


def _ensure_mentorship_allowed(mentee: MenteeProfile) -> None:
    """DPDP: minors must have guardian consent before contacting mentors."""
    if mentee.guardian_consent_status == GuardianConsentStatus.PENDING:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Guardian Consent Required",
        )


class MentorshipRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_request(self, mentee_user_id: uuid.UUID, body: MentorshipRequestCreate) -> MentorshipRequest:
        mentee = await self._session.scalar(
            select(MenteeProfile).where(MenteeProfile.user_id == mentee_user_id),
        )
        if mentee is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Mentee profile not found; create one with POST /profiles/mentee",
            )

        _ensure_mentorship_allowed(mentee)

        mentor = await self._session.scalar(
            select(MentorProfile).where(MentorProfile.user_id == body.mentor_id),
        )
        if mentor is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Mentor profile not found")

        if not mentor.is_accepting_requests:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Mentor is not accepting requests",
            )

        dup = await self._session.scalar(
            select(MentorshipRequest).where(
                MentorshipRequest.mentee_id == mentee.id,
                MentorshipRequest.mentor_id == mentor.id,
                MentorshipRequest.status == MentorshipRequestStatus.PENDING,
            ),
        )
        if dup is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="A pending request already exists for this mentor",
            )

        req = MentorshipRequest(
            mentee_id=mentee.id,
            mentor_id=mentor.id,
            status=MentorshipRequestStatus.PENDING,
            intro_message=body.intro_message,
        )
        self._session.add(req)
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="A pending request already exists for this mentor",
            ) from e
        await self._session.refresh(req)
        return req

    async def get_incoming_requests(self, mentor_user_id: uuid.UUID) -> list[dict]:
        mentor = await self._session.scalar(
            select(MentorProfile).where(MentorProfile.user_id == mentor_user_id),
        )
        if mentor is None:
            return []
        
        stmt = (
            select(MentorshipRequest, MenteeProfile.first_name, MenteeProfile.last_name)
            .join(MenteeProfile, MentorshipRequest.mentee_id == MenteeProfile.id)
            .where(
                MentorshipRequest.mentor_id == mentor.id,
                MentorshipRequest.status == MentorshipRequestStatus.PENDING,
            )
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for req, fn, ln in results:
            d = {
                "id": req.id,
                "mentee_id": req.mentee_id,
                "mentor_id": req.mentor_id,
                "status": req.status,
                "intro_message": req.intro_message,
                "mentee_name": f"{fn or ''} {ln or ''}".strip() or "Mentee",
            }
            out.append(d)
        return out

    async def get_outgoing_requests(self, mentee_user_id: uuid.UUID) -> list[dict]:
        mentee = await self._session.scalar(
            select(MenteeProfile).where(MenteeProfile.user_id == mentee_user_id),
        )
        if mentee is None:
            return []
            
        stmt = (
            select(MentorshipRequest, MentorProfile.first_name, MentorProfile.last_name)
            .join(MentorProfile, MentorshipRequest.mentor_id == MentorProfile.id)
            .where(MentorshipRequest.mentee_id == mentee.id)
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for req, fn, ln in results:
            d = {
                "id": req.id,
                "mentee_id": req.mentee_id,
                "mentor_id": req.mentor_id,
                "status": req.status,
                "intro_message": req.intro_message,
                "mentor_name": f"{fn or ''} {ln or ''}".strip() or "Mentor",
            }
            out.append(d)
        return out

    async def get_goals(self, connection_id: uuid.UUID) -> list[dict]:
        from app.models import Goal
        stmt = select(Goal).where(Goal.connection_id == connection_id)
        results = (await self._session.execute(stmt)).scalars().all()
        return [{"id": str(r.id), "title": r.title, "status": r.status} for r in results]

    async def get_vault(self, connection_id: uuid.UUID) -> list[dict]:
        from app.models import Session as MentorshipSession, SessionHistory, TimeSlot
        stmt = (
            select(MentorshipSession, SessionHistory, TimeSlot)
            .join(SessionHistory, SessionHistory.session_id == MentorshipSession.id)
            .join(TimeSlot, MentorshipSession.slot_id == TimeSlot.id)
            .where(MentorshipSession.connection_id == connection_id)
            .order_by(TimeSlot.start_time.desc())
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for sess, hist, slot in results:
            out.append({
                "session_id": str(sess.id),
                "start_time": slot.start_time,
                "notes": hist.notes_data or {},
                "mentor_rating": hist.mentor_rating,
                "mentee_rating": hist.mentee_rating,
            })
        return out
    async def get_session_history_stats(self, connection_id: uuid.UUID) -> list[dict]:
        from app.models import Session as MentorshipSession, TimeSlot
        stmt = (
            select(MentorshipSession, TimeSlot)
            .join(TimeSlot, TimeSlot.id == MentorshipSession.slot_id)
            .where(
                MentorshipSession.connection_id == connection_id,
                MentorshipSession.status == "COMPLETED"
            )
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for sess, slot in results:
            duration = 1.0
            if slot.start_time and slot.end_time:
                duration = (slot.end_time - slot.start_time).total_seconds() / 3600.0
            out.append({
                "session_id": str(sess.id),
                "duration_hours": duration,
                "start_time": slot.start_time.isoformat() if slot.start_time else None
            })
        return out

    async def get_active_connections(self, user_id: uuid.UUID) -> list[dict]:
        # User could be mentor or mentee
        mentor = await self._session.scalar(select(MentorProfile).where(MentorProfile.user_id == user_id))
        mentee = await self._session.scalar(select(MenteeProfile).where(MenteeProfile.user_id == user_id))
        
        mentor_id = mentor.id if mentor else None
        mentee_id = mentee.id if mentee else None
        
        from app.models import User
        MentorUser = aliased(User)
        MenteeUser = aliased(User)
        stmt = (
            select(
                MentorshipConnection, 
                MentorProfile.first_name.label("m_fn"), 
                MentorProfile.last_name.label("m_ln"),
                MenteeProfile.first_name.label("me_fn"),
                MenteeProfile.last_name.label("me_ln"),
                MentorProfile.user_id.label("m_uid"),
                MenteeProfile.user_id.label("me_uid"),
                MentorUser.email.label("m_email"),
                MenteeUser.email.label("me_email")
            )
            .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
            .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
            .join(MentorUser, MentorProfile.user_id == MentorUser.id)
            .join(MenteeUser, MenteeProfile.user_id == MenteeUser.id)
            .where(
                (MentorshipConnection.mentor_id == mentor_id) | 
                (MentorshipConnection.mentee_id == mentee_id),
                MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE
            )
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for row in results:
            conn = row[0]
            d = {
                "id": str(conn.id),
                "mentee_id": str(conn.mentee_id),
                "mentor_id": str(conn.mentor_id),
                "mentee_user_id": str(row.me_uid),
                "mentor_user_id": str(row.m_uid),
                "mentee_email": row.me_email,
                "mentor_email": row.m_email,
                "status": "ACCEPTED",
                "intro_message": "Active Connection",
                "mentee_name": f"{row.me_fn or ''} {row.me_ln or ''}".strip() or "Mentee",
                "mentor_name": f"{row.m_fn or ''} {row.m_ln or ''}".strip() or "Mentor",
            }
            out.append(d)
        return out

    async def admin_list_all_connections(self) -> list[dict]:
        from app.models import User
        MentorUser = aliased(User)
        MenteeUser = aliased(User)
        stmt = (
            select(
                MentorshipConnection,
                MentorProfile.user_id.label("m_uid"),
                MenteeProfile.user_id.label("me_uid"),
                MentorUser.email.label("m_email"),
                MenteeUser.email.label("me_email")
            )
            .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
            .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
            .join(MentorUser, MentorProfile.user_id == MentorUser.id)
            .join(MenteeUser, MenteeProfile.user_id == MenteeUser.id)
            .where(MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE)
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for row in results:
            conn = row[0]
            out.append({
                "id": str(conn.id),
                "mentor_id": str(conn.mentor_id),
                "mentee_id": str(conn.mentee_id),
                "mentor_user_id": str(row.m_uid),
                "mentee_user_id": str(row.me_uid),
                "mentor_email": row.m_email,
                "mentee_email": row.me_email,
                "status": "ACTIVE"
            })
        return out

    async def update_status(
        self,
        request_id: uuid.UUID,
        acting_user_id: uuid.UUID,
        body: MentorshipRequestStatusUpdate,
    ) -> dict:
        req = await self._session.get(MentorshipRequest, request_id)
        if req is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")

        mentor = await self._session.get(MentorProfile, req.mentor_id)
        if mentor is None or mentor.user_id != acting_user_id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Only the mentor can update this request",
            )

        mentee = await self._session.get(MenteeProfile, req.mentee_id)
        if mentee is None:
             raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Mentee profile not found")

        if req.status != MentorshipRequestStatus.PENDING:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Request is no longer pending",
            )

        req.status = body.status

        if body.status == MentorshipRequestStatus.ACCEPTED:
            # Prevent duplicate connection errors
            existing = await self._session.scalar(
                select(MentorshipConnection).where(
                    MentorshipConnection.mentor_id == req.mentor_id,
                    MentorshipConnection.mentee_id == req.mentee_id
                )
            )
            if not existing:
                conn = MentorshipConnection(
                    mentee_id=req.mentee_id,
                    mentor_id=req.mentor_id,
                    status=MentorshipConnectionStatus.ACTIVE,
                )
                self._session.add(conn)
                await self._session.flush()
                try:
                    publish_event(
                        TOPIC_MENTORING_CONNECTIONS,
                        {
                            "event": "MENTORSHIP_REQUEST_ACCEPTED",
                            "connection_id": str(conn.id),
                            "mentor_id": str(req.mentor_id),
                            "mentee_id": str(req.mentee_id),
                        },
                    )
                except Exception as e:
                    # Don't let a notification failure roll back the actual connection
                    import logging
                    logging.getLogger(__name__).warning("Notification stub failed: %s", e)

        await self._session.commit()
        
        return {
            "id": req.id,
            "mentee_id": req.mentee_id,
            "mentor_id": req.mentor_id,
            "status": req.status,
            "intro_message": req.intro_message,
            "mentee_name": f"{mentee.first_name or ''} {mentee.last_name or ''}".strip() or "Mentee",
            "mentor_name": f"{mentor.first_name or ''} {mentor.last_name or ''}".strip() or "Mentor",
        }
