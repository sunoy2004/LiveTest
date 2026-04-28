from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, MentorshipConnection, MentorshipRequest, User
from app.services import event_bus


def create_request(
    db: Session,
    *,
    mentee_user_id: UUID,
    mentor_profile_id: UUID,
    intro_message: str,
) -> MentorshipRequest:
    mentee = (
        db.query(MenteeProfile).filter(MenteeProfile.user_id == mentee_user_id).first()
    )
    if mentee is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Mentee profile not found",
        )
    if mentee.guardian_consent_status == "PENDING":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Guardian Consent Required",
        )

    mentor = db.query(MentorProfile).filter(MentorProfile.id == mentor_profile_id).first()
    if mentor is None:
        # Fallback: check if mentor_profile_id is actually a user_id
        mentor = db.query(MentorProfile).filter(MentorProfile.user_id == mentor_profile_id).first()

    if mentor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Mentor profile not found")
    if not mentor.is_accepting_requests:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Mentor is not accepting requests",
        )

    dup = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.mentee_id == mentee.id,
            MentorshipRequest.mentor_id == mentor.id,
            MentorshipRequest.status == "PENDING",
        )
        .first()
    )
    if dup is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="A pending request already exists for this mentor",
        )

    req = MentorshipRequest(
        mentee_id=mentee.id,
        mentor_id=mentor.id,
        status="PENDING",
        intro_message=intro_message,
    )
    db.add(req)
    try:
        db.commit()
        db.refresh(req)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="A pending request already exists for this mentor",
        ) from e

    mentor_user = db.query(User).filter(User.id == mentor.user_id).one()
    event_bus.publish_connections_event(
        event_bus.TOPIC_MENTORSHIP_REQUESTED,
        {
            "request_id": str(req.id),
            "mentor_profile_id": str(mentor.id),
            "mentee_profile_id": str(mentee.id),
            "mentor_user_id": str(mentor_user.id),
            "mentee_user_id": str(mentee_user_id),
        },
        notify_user_ids=[mentor_user.id, mentee_user_id],
    )
    return req


def update_request_status(
    db: Session,
    *,
    request_id: UUID,
    acting_user_id: UUID,
    new_status: str,
) -> MentorshipRequest:
    req = db.query(MentorshipRequest).filter(MentorshipRequest.id == request_id).first()
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Request not found")

    mentor = db.query(MentorProfile).filter(MentorProfile.id == req.mentor_id).one()
    if mentor.user_id != acting_user_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only the mentor can update this request",
        )
    if req.status != "PENDING":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Request is no longer pending",
        )

    if new_status not in ("ACCEPTED", "DECLINED"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="status must be ACCEPTED or DECLINED",
        )

    req.status = new_status

    conn: MentorshipConnection | None = None
    if new_status == "ACCEPTED":
        existing = (
            db.query(MentorshipConnection)
            .filter(
                MentorshipConnection.mentor_id == req.mentor_id,
                MentorshipConnection.mentee_id == req.mentee_id,
                MentorshipConnection.status == "ACTIVE",
            )
            .first()
        )
        if not existing:
            conn = MentorshipConnection(
                mentee_id=req.mentee_id,
                mentor_id=req.mentor_id,
                status="ACTIVE",
            )
            db.add(conn)
            db.flush()
        else:
            conn = existing

    db.commit()
    db.refresh(req)

    if new_status == "ACCEPTED" and conn is not None:
        mentee = db.query(MenteeProfile).filter(MenteeProfile.id == req.mentee_id).one()
        mentor_user = db.query(User).filter(User.id == mentor.user_id).one()
        mentee_user = db.query(User).filter(User.id == mentee.user_id).one()
        event_bus.publish_connections_event(
            event_bus.TOPIC_MENTORSHIP_ACCEPTED,
            {
                "connection_id": str(conn.id),
                "mentor_profile_id": str(req.mentor_id),
                "mentee_profile_id": str(req.mentee_id),
                "mentor_user_id": str(mentor_user.id),
                "mentee_user_id": str(mentee_user.id),
            },
            notify_user_ids=[mentor_user.id, mentee_user.id],
        )

    return req


def list_incoming_requests(db: Session, *, mentor_user_id: UUID):
    mentor = db.query(MentorProfile).filter(MentorProfile.user_id == mentor_user_id).first()
    if not mentor:
        return []
    
    query = (
        db.query(MentorshipRequest, User.email)
        .join(MenteeProfile, MentorshipRequest.mentee_id == MenteeProfile.id)
        .join(User, MenteeProfile.user_id == User.id)
        .filter(
            MentorshipRequest.mentor_id == mentor.id,
            MentorshipRequest.status == "PENDING"
        )
        .order_by(MentorshipRequest.created_at.desc())
    )
    
    results = []
    for req, email in query.all():
        local = (email or "").split("@", 1)[0]
        mentee_name = local.replace("_", " ").replace(".", " ").title() or "Mentee"
        
        results.append({
            "id": req.id,
            "mentee_id": req.mentee_id,
            "mentor_id": req.mentor_id,
            "status": req.status,
            "intro_message": req.intro_message,
            "mentee_name": mentee_name
        })
    return results
