"""POST /api/v1/sessions/{session_id}/history — append or merge vault notes for a session."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, MentorshipConnection, SessionHistory, User
from app.models import Session as MentorshipSession


async def create_history_entry(
    db: Session,
    *,
    user: User,
    session_id: UUID,
    notes: dict,
) -> dict:
    row = (
        db.query(MentorshipSession)
        .filter(MentorshipSession.id == session_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.id == row.connection_id)
        .one_or_none()
    )
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")

    mp = db.query(MentorProfile).filter(MentorProfile.id == conn.mentor_id).one()
    me = db.query(MenteeProfile).filter(MenteeProfile.id == conn.mentee_id).one()
    if user.id not in (mp.user_id, me.user_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Not a member of this session's connection",
        )

    existing = (
        db.query(SessionHistory)
        .filter(SessionHistory.session_id == row.id)
        .first()
    )
    payload = notes if isinstance(notes, dict) else {"data": notes}
    if existing is not None:
        merged = dict(existing.notes_data or {})
        merged.update(payload)
        existing.notes_data = merged
    else:
        db.add(
            SessionHistory(
                session_id=row.id,
                notes_data=payload,
                mentor_rating=None,
                mentee_rating=None,
            )
        )
    db.commit()
    return {"session_id": str(session_id), "status": "ok"}
