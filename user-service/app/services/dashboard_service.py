from datetime import datetime, timedelta, timezone
import os
import uuid
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.models import (
    Goal,
    MenteeProfile,
    MentorProfile,
    MentorshipConnection,
    SessionBookingRequest,
    SessionHistory,
    TimeSlot,
    User,
)
from app.models import Session as MentorshipSession
from app.services.mentor_pricing import resolve_mentor_session_price


def _partner_display_name(user_row: User | None) -> str:
    if not user_row or not user_row.email:
        return "Partner"
    local = user_row.email.split("@")[0]
    return local.replace(".", " ").replace("_", " ").title()


def _effective_context(
    *,
    context: str | None,
    has_mentor: bool,
    has_mentee: bool,
) -> str | None:
    if context in ("mentor", "mentee"):
        return context
    if has_mentee and not has_mentor:
        return "mentee"
    if has_mentor and not has_mentee:
        return "mentor"
    if has_mentor and has_mentee:
        return "mentee"
    return None


def _fetch_connections_from_db(mentoring_db: Session, user_id: uuid.UUID) -> list[dict]:
    """Directly query Mentoring DB for active connections for a user."""
    # First find the profile IDs in the mentoring DB
    mentor = mentoring_db.query(MentorProfile).filter(MentorProfile.user_id == user_id).first()
    mentee = mentoring_db.query(MenteeProfile).filter(MenteeProfile.user_id == user_id).first()
    
    mentor_id = mentor.id if mentor else None
    mentee_id = mentee.id if mentee else None
    
    if not mentor_id and not mentee_id:
        return []

    q = (
        mentoring_db.query(MentorshipConnection, MentorProfile.user_id.label("m_uid"), MenteeProfile.user_id.label("me_uid"))
        .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
        .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
        .filter(
            or_(
                MentorshipConnection.mentor_id == mentor_id,
                MentorshipConnection.mentee_id == mentee_id
            ),
            MentorshipConnection.status == "ACTIVE"
        )
    )
    
    out = []
    for conn, m_uid, me_uid in q.all():
        out.append({
            "id": str(conn.id),
            "mentee_id": str(conn.mentee_id),
            "mentor_id": str(conn.mentor_id),
            "mentee_user_id": str(me_uid),
            "mentor_user_id": str(m_uid),
            "status": "ACTIVE"
        })
    return out


def _fetch_admin_all_connections(mentoring_db: Session) -> list[dict]:
    """Directly query Mentoring DB for all active connections."""
    q = (
        mentoring_db.query(MentorshipConnection)
        .filter(MentorshipConnection.status == "ACTIVE")
    )
    return [{
        "id": str(c.id),
        "mentee_id": str(c.mentee_id),
        "mentor_id": str(c.mentor_id),
        "status": "ACTIVE"
    } for c in q.all()]


def resolve_connection(
    db: Session,
    mentoring_db: Session,
    *,
    user: User,
    context: str | None,
) -> tuple[dict | None, bool | None]:
    """
    Returns (connection_dict, viewer_is_mentor).
    Fetches connection data from Mentoring DB instead of API.
    """
    conns = _fetch_connections_from_db(mentoring_db, user.id)
    if not conns:
        return None, None

    mentor_profile = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
    mentee_profile = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    
    has_mentor = mentor_profile is not None
    has_mentee = mentee_profile is not None

    eff = _effective_context(
        context=context,
        has_mentor=has_mentor,
        has_mentee=has_mentee,
    )
    
    if eff == "mentor" and mentor_profile:
        for c in conns:
            if str(c["mentor_user_id"]) == str(user.id):
                return c, True
    
    if eff == "mentee" and mentee_profile:
        for c in conns:
            if str(c["mentee_user_id"]) == str(user.id):
                return c, False

    return None, None


def _session_price_for_row(
    db: Session,
    row: MentorshipSession,
    sess_conn: dict,
) -> int:
    if row.price_charged is not None:
        return int(row.price_charged)
    # We use mentor_user_id to find the profile in User DB
    mp = (
        db.query(MentorProfile)
        .filter(MentorProfile.user_id == UUID(str(sess_conn["mentor_user_id"])))
        .one()
    )
    return resolve_mentor_session_price(db, mp)


def _mentor_mentee_brief(
    db: Session,
    sess_conn: dict,
) -> tuple[dict, dict]:
    mentor_user_id = UUID(str(sess_conn["mentor_user_id"]))
    mentee_user_id = UUID(str(sess_conn["mentee_user_id"]))
    mp = db.query(MentorProfile).filter(MentorProfile.user_id == mentor_user_id).one()
    me = db.query(MenteeProfile).filter(MenteeProfile.user_id == mentee_user_id).one()
    mentor_user = db.query(User).filter(User.id == mp.user_id).one()
    mentee_user = db.query(User).filter(User.id == me.user_id).one()
    
    mentor_brief = {
        "id": mp.id,
        "name": _partner_display_name(mentor_user),
        "expertise": mp.expertise_areas or [],
    }
    mentee_brief = {
        "id": me.id,
        "name": _partner_display_name(mentee_user),
    }
    return mentor_brief, mentee_brief


def _partner_user_for_connection(
    db: Session,
    conn: dict,
    *,
    viewer_is_mentor: bool,
) -> User | None:
    if viewer_is_mentor:
        mentee_user_id = UUID(str(conn["mentee_user_id"]))
        return db.query(User).filter(User.id == mentee_user_id).first()
    
    mentor_user_id = UUID(str(conn["mentor_user_id"]))
    return db.query(User).filter(User.id == mentor_user_id).first()


def _active_connection_ids_for_viewer(mentoring_db: Session, *, user: User, viewer_is_mentor: bool) -> list[UUID]:
    conns = _fetch_connections_from_db(mentoring_db, user.id)
    if not conns:
        return []
        
    if viewer_is_mentor:
        return [UUID(str(c["id"])) for c in conns if str(c["mentor_user_id"]) == str(user.id)]
    else:
        return [UUID(str(c["id"])) for c in conns if str(c["mentee_user_id"]) == str(user.id)]


async def _collect_upcoming_payloads(
    db: Session,
    *,
    viewer_is_mentor: bool,
    conn_ids: list[UUID],
    mentor_profile: MentorProfile | None,
    include_rejected_booking_requests: bool,
    max_items: int,
) -> list[dict]:
    cap = max(1, min(max_items, 20))
    sched = (
        db.query(MentorshipSession)
        .filter(
            MentorshipSession.connection_id.in_(conn_ids),
            MentorshipSession.status == "SCHEDULED",
        )
        .order_by(MentorshipSession.start_time.asc())
        .limit(50)
        .all()
    )

    booking_pairs: list[tuple[SessionBookingRequest, TimeSlot]] = []
    if viewer_is_mentor and mentor_profile is not None:
        booking_pairs = (
            db.query(SessionBookingRequest, TimeSlot)
            .join(TimeSlot, TimeSlot.id == SessionBookingRequest.slot_id)
            .filter(
                SessionBookingRequest.connection_id.in_(conn_ids),
                SessionBookingRequest.status == "PENDING",
            )
            .order_by(TimeSlot.start_time.asc())
            .limit(50)
            .all()
        )
    elif not viewer_is_mentor:
        st = ("PENDING", "REJECTED") if include_rejected_booking_requests else ("PENDING",)
        booking_pairs = (
            db.query(SessionBookingRequest, TimeSlot)
            .join(TimeSlot, TimeSlot.id == SessionBookingRequest.slot_id)
            .filter(
                SessionBookingRequest.connection_id.in_(conn_ids),
                SessionBookingRequest.status.in_(st),
            )
            .order_by(TimeSlot.start_time.asc())
            .limit(50)
            .all()
        )

    out = []
    for row in sched:
        out.append({
            "type": "SESSION",
            "id": row.id,
            "connection_id": row.connection_id,
            "start_time": row.start_time,
            "status": row.status,
            "meeting_url": row.meeting_url,
        })
    for req, slot in booking_pairs:
        out.append({
            "type": "BOOKING_REQUEST",
            "id": req.id,
            "connection_id": req.connection_id,
            "start_time": slot.start_time,
            "status": req.status,
            "agreed_cost": req.agreed_cost,
        })

    out.sort(key=lambda x: x["start_time"])
    return out[:cap]


async def get_upcoming_sessions(db: Session, mentoring_db: Session, *, user: User, context: str | None, limit: int = 5) -> list[dict]:
    mentor_profile = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
    mentee_profile = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    
    eff = _effective_context(context=context, has_mentor=mentor_profile is not None, has_mentee=mentee_profile is not None)
    viewer_is_mentor = (eff == "mentor")
    
    conn_ids = _active_connection_ids_for_viewer(mentoring_db, user=user, viewer_is_mentor=viewer_is_mentor)
    if not conn_ids:
        return []

    return await _collect_upcoming_payloads(
        db,
        viewer_is_mentor=viewer_is_mentor,
        conn_ids=conn_ids,
        mentor_profile=mentor_profile if viewer_is_mentor else None,
        include_rejected_booking_requests=not viewer_is_mentor,
        max_items=limit
    )


async def get_goals(db: Session, mentoring_db: Session, *, user: User, context: str | None) -> list[dict]:
    conn, _ = resolve_connection(db, mentoring_db, user=user, context=context)
    if not conn:
        return []
    
    # Goals are stored in Mentoring DB
    results = mentoring_db.query(Goal).filter(Goal.connection_id == UUID(conn["id"])).all()
    return [{"id": str(g.id), "title": g.title, "status": g.status} for g in results]


async def get_vault(db: Session, mentoring_db: Session, *, user: User, context: str | None) -> list[dict]:
    conn, viewer_is_mentor = resolve_connection(db, mentoring_db, user=user, context=context)
    if not conn:
        return []
    
    # Sessions are in User DB
    cid = UUID(conn["id"])
    history = (
        db.query(MentorshipSession, SessionHistory)
        .join(SessionHistory, SessionHistory.session_id == MentorshipSession.id)
        .filter(MentorshipSession.connection_id == cid)
        .order_by(MentorshipSession.start_time.desc())
        .all()
    )
    
    out = []
    for sess, hist in history:
        out.append({
            "session_id": str(sess.id),
            "start_time": sess.start_time,
            "notes": hist.notes_data or {},
            "mentor_rating": hist.mentor_rating,
            "mentee_rating": hist.mentee_rating,
        })
    return out


async def get_dashboard_stats(db: Session, mentoring_db: Session, *, user: User, context: str | None) -> dict:
    if user.is_admin:
        all_conns = _fetch_admin_all_connections(mentoring_db)
        # Note: Profiles IDs are DB-specific, but in mentoring DB they are unique mentors/mentees
        unique_mentors = len(set(str(c["mentor_id"]) for c in all_conns))
        unique_mentees = len(set(str(c["mentee_id"]) for c in all_conns))
        
        # Admin hours/sessions come from User DB
        history = db.query(MentorshipSession).filter(MentorshipSession.status == "COMPLETED").all()
        sessions_completed = len(history)
        
        active_ct = db.query(MentorshipSession).filter(MentorshipSession.status == "SCHEDULED").count()
        
        return {
            "active_partners": unique_mentors if context != "mentor" else unique_mentees,
            "hours_total": sessions_completed, # Approximation
            "hours_this_week": 0,
            "sessions_completed": sessions_completed,
            "active_sessions": active_ct,
        }

    mentor_profile = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
    mentee_profile = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    
    eff = _effective_context(context=context, has_mentor=mentor_profile is not None, has_mentee=mentee_profile is not None)
    viewer_is_mentor = (eff == "mentor")
    
    conn_ids = _active_connection_ids_for_viewer(mentoring_db, user=user, viewer_is_mentor=viewer_is_mentor)
    if not conn_ids:
        return {
            "active_partners": 0,
            "hours_total": 0,
            "hours_this_week": 0,
            "sessions_completed": 0,
            "active_sessions": 0,
        }

    # Hours come from User DB
    history = db.query(MentorshipSession).filter(
        MentorshipSession.connection_id.in_(conn_ids),
        MentorshipSession.status == "COMPLETED"
    ).all()
    
    sessions_completed = len(history)
    hours_total = 0.0
    hours_week = 0.0
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    for row in history:
        # Assuming 1 hour per session for simplicity if slot duration isn't joined
        h = 1.0
        hours_total += h
        if row.start_time:
            st_aware = row.start_time if row.start_time.tzinfo else row.start_time.replace(tzinfo=timezone.utc)
            if st_aware >= week_ago:
                hours_week += h

    active_ct = (
        db.query(MentorshipSession)
        .filter(
            MentorshipSession.connection_id.in_(conn_ids),
            MentorshipSession.status == "SCHEDULED",
        )
        .count()
    )

    return {
        "active_partners": len(conn_ids),
        "hours_total": hours_total,
        "hours_this_week": hours_week,
        "sessions_completed": sessions_completed,
        "active_sessions": active_ct,
    }
