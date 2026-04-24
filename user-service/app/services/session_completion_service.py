from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, MentorshipConnection, SessionHistory
from app.models import Session as MentorshipSession
from app.models import User
from app.services import event_bus

log = logging.getLogger(__name__)


def _connection_party_user_ids(db: Session, conn: MentorshipConnection) -> tuple[UUID, UUID]:
    mp = db.query(MentorProfile).filter(MentorProfile.id == conn.mentor_id).one()
    me = db.query(MenteeProfile).filter(MenteeProfile.id == conn.mentee_id).one()
    return mp.user_id, me.user_id


def complete_session(
    db: Session,
    *,
    user: User,
    session_id: UUID,
) -> MentorshipSession:
    row = (
        db.query(MentorshipSession)
        .filter(MentorshipSession.id == session_id)
        .with_for_update()
        .one_or_none()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.id == row.connection_id)
        .one()
    )
    mentor_uid, mentee_uid = _connection_party_user_ids(db, conn)
    if user.id not in (mentor_uid, mentee_uid):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this session's connection")
    if row.status != "SCHEDULED":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only SCHEDULED sessions can be completed",
        )

    row.status = "COMPLETED"
    existing = (
        db.query(SessionHistory)
        .filter(SessionHistory.session_id == row.id)
        .first()
    )
    if not existing:
        db.add(
            SessionHistory(
                session_id=row.id,
                notes_data={"summary": "Session marked complete", "auto": True},
                mentor_rating=None,
                mentee_rating=None,
            )
        )
    db.commit()
    db.refresh(row)

    log.info(
        "session completed session_id=%s mentor_user_id=%s mentee_user_id=%s (gamification rewards via Redis)",
        row.id,
        mentor_uid,
        mentee_uid,
    )

    event_bus.publish_event(
        event_bus.TOPIC_SESSION_COMPLETED,
        {
            "session_id": str(row.id),
            "connection_id": str(conn.id),
            "start_time": row.start_time.isoformat(),
            "mentor_user_id": str(mentor_uid),
            "mentee_user_id": str(mentee_uid),
        },
        notify_user_ids=[mentor_uid, mentee_uid],
    )
    return row
