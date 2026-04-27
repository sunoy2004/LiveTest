import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
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
            select(MentorshipRequest, MenteeProfile.full_name)
            .join(MenteeProfile, MentorshipRequest.mentee_id == MenteeProfile.id)
            .where(
                MentorshipRequest.mentor_id == mentor.id,
                MentorshipRequest.status == MentorshipRequestStatus.PENDING,
            )
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for req, name in results:
            d = {
                "id": req.id,
                "mentee_id": req.mentee_id,
                "mentor_id": req.mentor_id,
                "status": req.status,
                "intro_message": req.intro_message,
                "mentee_name": name,
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
            select(MentorshipRequest, MentorProfile.full_name)
            .join(MentorProfile, MentorshipRequest.mentor_id == MentorProfile.id)
            .where(MentorshipRequest.mentee_id == mentee.id)
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for req, name in results:
            d = {
                "id": req.id,
                "mentee_id": req.mentee_id,
                "mentor_id": req.mentor_id,
                "status": req.status,
                "intro_message": req.intro_message,
                "mentor_name": name,
            }
            out.append(d)
        return out

    async def get_goals(self, connection_id: uuid.UUID) -> list[dict]:
        from app.models import Goal
        stmt = select(Goal).where(Goal.connection_id == connection_id)
        results = (await self._session.execute(stmt)).scalars().all()
        return [{"id": str(r.id), "title": r.title, "status": r.status} for r in results]

    async def get_vault(self, connection_id: uuid.UUID) -> list[dict]:
        from app.models import MentorshipSession, SessionHistory
        stmt = (
            select(MentorshipSession, SessionHistory)
            .join(SessionHistory, SessionHistory.session_id == MentorshipSession.id)
            .where(MentorshipSession.connection_id == connection_id)
            .order_by(MentorshipSession.start_time.desc())
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for sess, hist in results:
            out.append({
                "session_id": str(sess.id),
                "start_time": sess.start_time,
                "notes": hist.notes_data or {},
                "mentor_rating": hist.mentor_rating,
                "mentee_rating": hist.mentee_rating,
            })
        return out

    async def get_active_connections(self, user_id: uuid.UUID) -> list[dict]:
        # User could be mentor or mentee
        mentor = await self._session.scalar(select(MentorProfile).where(MentorProfile.user_id == user_id))
        mentee = await self._session.scalar(select(MenteeProfile).where(MenteeProfile.user_id == user_id))
        
        mentor_id = mentor.id if mentor else None
        mentee_id = mentee.id if mentee else None
        
        stmt = (
            select(MentorshipConnection, MentorProfile.full_name, MenteeProfile.full_name)
            .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
            .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
            .where(
                (MentorshipConnection.mentor_id == mentor_id) | 
                (MentorshipConnection.mentee_id == mentee_id),
                MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE
            )
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for conn, m_name, me_name in results:
            d = {
                "id": conn.id,
                "mentee_id": conn.mentee_id,
                "mentor_id": conn.mentor_id,
                "status": MentorshipRequestStatus.ACCEPTED, # Match schema expectation
                "intro_message": "Active Connection",
                "mentee_name": me_name,
                "mentor_name": m_name,
            }
            out.append(d)
        return out

    async def admin_list_all_connections(self) -> list[dict]:
        stmt = (
            select(
                MentorshipConnection,
                MentorProfile.user_id.label("mentor_user_id"),
                MenteeProfile.user_id.label("mentee_user_id")
            )
            .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
            .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
            .where(MentorshipConnection.status == MentorshipConnectionStatus.ACTIVE)
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for conn, m_uid, me_uid in results:
            out.append({
                "id": str(conn.id),
                "mentor_id": str(conn.mentor_id),
                "mentee_id": str(conn.mentee_id),
                "mentor_user_id": str(m_uid),
                "mentee_user_id": str(me_uid),
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
            "mentee_name": mentee.full_name,
            "mentor_name": mentor.full_name,
        }
