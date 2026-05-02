import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import desc, select, or_, and_
from sqlalchemy.orm import aliased
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.publisher import publish_event
from app.utils.display_name import from_email
from app.models import (
    MenteeProfile,
    MentorProfile,
    MentorshipConnection,
    MentorshipRequest,
    User,
)
from app.models.enums import (
    GuardianConsentStatus,
    MentorshipConnectionStatus,
    MentorshipRequestStatus,
)
from app.schemas.request import MentorshipRequestCreate, MentorshipRequestStatusUpdate
from app.constants.mentorship_request import DEFAULT_INTRO_MESSAGE

TOPIC_MENTORING_CONNECTIONS = "mentoring.connections.events"


def _resolved_intro_message(raw: str | None) -> str:
    s = (raw or "").strip()
    return s if s else DEFAULT_INTRO_MESSAGE


def _ensure_mentorship_allowed(mentee: MenteeProfile) -> None:
    """DPDP: minors must have guardian consent before contacting mentors."""
    if hasattr(mentee, "guardian_consent_status") and mentee.guardian_consent_status == GuardianConsentStatus.PENDING:
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
                detail="Mentee profile not found",
            )

        _ensure_mentorship_allowed(mentee)

        mentor = await self._session.scalar(
            select(MentorProfile).where(MentorProfile.user_id == body.mentor_id),
        )
        if mentor is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Mentor profile not found")

        dup = await self._session.scalar(
            select(MentorshipRequest).where(
                MentorshipRequest.sender_user_id == mentee_user_id,
                MentorshipRequest.receiver_user_id == body.mentor_id,
                MentorshipRequest.status == MentorshipRequestStatus.PENDING,
            ),
        )
        if dup is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="A pending request already exists",
            )

        pitch = _resolved_intro_message(body.intro_message)
        req = MentorshipRequest(
            sender_user_id=mentee_user_id,
            receiver_user_id=body.mentor_id,
            status=MentorshipRequestStatus.PENDING,
            intro_message=pitch,
        )
        self._session.add(req)
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Request already exists",
            ) from e
        await self._session.refresh(req)
        return req

    async def get_incoming_requests(self, mentor_user_id: uuid.UUID) -> list[dict]:
        stmt = (
            select(MentorshipRequest, User.email)
            .join(User, MentorshipRequest.sender_user_id == User.user_id)
            .where(
                MentorshipRequest.receiver_user_id == mentor_user_id,
                MentorshipRequest.status == MentorshipRequestStatus.PENDING,
            )
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for req, email in results:
            intro = getattr(req, "intro_message", None) or ""
            d = {
                "sender_user_id": str(req.sender_user_id),
                "receiver_user_id": str(req.receiver_user_id),
                "status": req.status,
                "mentee_name": from_email(email),
                "intro_message": intro,
            }
            out.append(d)
        return out

    async def get_outgoing_requests(self, mentee_user_id: uuid.UUID) -> list[dict]:
        stmt = (
            select(MentorshipRequest, User.email)
            .join(User, MentorshipRequest.receiver_user_id == User.user_id)
            .where(MentorshipRequest.sender_user_id == mentee_user_id)
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for req, email in results:
            d = {
                "sender_user_id": str(req.sender_user_id),
                "receiver_user_id": str(req.receiver_user_id),
                "status": req.status,
                "mentor_name": from_email(email),
            }
            out.append(d)
        return out

    async def list_request_history(self, user_id: uuid.UUID, *, limit: int = 100) -> list[dict]:
        """All `mentorship_requests` where the user is sender (mentee) or receiver (mentor)."""
        limit = max(1, min(int(limit), 200))
        SenderUser = aliased(User)
        ReceiverUser = aliased(User)
        stmt = (
            select(MentorshipRequest, SenderUser.email, ReceiverUser.email)
            .join(SenderUser, MentorshipRequest.sender_user_id == SenderUser.user_id)
            .join(ReceiverUser, MentorshipRequest.receiver_user_id == ReceiverUser.user_id)
            .where(
                or_(
                    MentorshipRequest.sender_user_id == user_id,
                    MentorshipRequest.receiver_user_id == user_id,
                )
            )
            .order_by(desc(MentorshipRequest.created_at))
            .limit(limit)
        )
        results = (await self._session.execute(stmt)).all()
        uid_str = str(user_id)
        out: list[dict] = []
        for req, sender_email, receiver_email in results:
            intro = getattr(req, "intro_message", None) or ""
            out.append(
                {
                    "sender_user_id": str(req.sender_user_id),
                    "receiver_user_id": str(req.receiver_user_id),
                    "status": req.status,
                    "intro_message": intro,
                    "created_at": req.created_at.isoformat() if req.created_at else None,
                    "mentee_name": from_email(sender_email),
                    "mentor_name": from_email(receiver_email),
                    "you_are": "mentor"
                    if uid_str == str(req.receiver_user_id)
                    else "mentee",
                }
            )
        return out

    async def get_goals_by_users(self, mentor_id: uuid.UUID, mentee_id: uuid.UUID) -> list[dict]:
        from app.models import Goal
        stmt = select(Goal).where(
            Goal.user_id.in_([mentor_id, mentee_id])
        )
        results = (await self._session.execute(stmt)).scalars().all()
        return [{"id": str(r.user_id), "goal": r.goal} for r in results]

    async def get_active_connections(self, user_id: uuid.UUID) -> list[dict]:
        MentorUser = aliased(User)
        MenteeUser = aliased(User)
        stmt = (
            select(MentorshipConnection, MentorUser.email, MenteeUser.email)
            .join(MentorUser, MentorshipConnection.mentor_user_id == MentorUser.user_id)
            .join(MenteeUser, MentorshipConnection.mentee_user_id == MenteeUser.user_id)
            .where(
                or_(
                    MentorshipConnection.mentor_user_id == user_id,
                    MentorshipConnection.mentee_user_id == user_id
                ),
                MentorshipConnection.status == "ACTIVE"
            )
        )
        results = (await self._session.execute(stmt)).all()
        out = []
        for conn, mentor_email, mentee_email in results:
            d = {
                "mentor_user_id": str(conn.mentor_user_id),
                "mentee_user_id": str(conn.mentee_user_id),
                "status": conn.status,
                "mentor_name": from_email(mentor_email),
                "mentee_name": from_email(mentee_email),
            }
            out.append(d)
        return out

    async def update_status(
        self,
        sender_user_id: uuid.UUID,
        receiver_user_id: uuid.UUID,
        acting_user_id: uuid.UUID,
        body: MentorshipRequestStatusUpdate,
    ) -> dict:
        stmt = select(MentorshipRequest).where(
            MentorshipRequest.sender_user_id == sender_user_id,
            MentorshipRequest.receiver_user_id == receiver_user_id
        )
        req = await self._session.scalar(stmt)
        if req is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")

        if receiver_user_id != acting_user_id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Only the receiver can update this request",
            )

        if req.status != MentorshipRequestStatus.PENDING:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Request is no longer pending",
            )

        req.status = body.status

        if body.status == "ACCEPTED":
            existing = await self._session.scalar(
                select(MentorshipConnection).where(
                    MentorshipConnection.mentor_user_id == receiver_user_id,
                    MentorshipConnection.mentee_user_id == sender_user_id
                )
            )
            if not existing:
                conn = MentorshipConnection(
                    mentor_user_id=receiver_user_id,
                    mentee_user_id=sender_user_id,
                    status="ACTIVE",
                )
                self._session.add(conn)
                try:
                    publish_event(
                        TOPIC_MENTORING_CONNECTIONS,
                        {
                            "event": "MENTORSHIP_REQUEST_ACCEPTED",
                            "mentor_user_id": str(receiver_user_id),
                            "mentee_user_id": str(sender_user_id),
                        },
                    )
                except:
                    pass

        await self._session.commit()
        return {
            "sender_user_id": str(req.sender_user_id),
            "receiver_user_id": str(req.receiver_user_id),
            "status": req.status,
        }
