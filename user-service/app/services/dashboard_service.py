from datetime import datetime, timedelta, timezone
import os
import uuid
from uuid import UUID
import httpx
from sqlalchemy.orm import Session

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


MENTORING_SERVICE_URL = os.getenv(
    "MENTORING_SERVICE_URL", 
    "https://mentoring-service-1095720168864-1095720168864.us-central1.run.app"
)


async def _fetch_connections_from_service(user_id: uuid.UUID) -> list[dict]:
    """Call Mentoring Service to get active connections for a user."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{MENTORING_SERVICE_URL}/api/v1/requests/connections",
                headers={"X-User-Id": str(user_id)}
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return []


async def _fetch_admin_all_connections() -> list[dict]:
    """Call Mentoring Service to get all active connections for admin view."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{MENTORING_SERVICE_URL}/api/v1/requests/admin/connections")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return []


async def resolve_connection(
    db: Session,
    *,
    user: User,
    context: str | None,
) -> tuple[dict | None, bool | None]:
    """
    Returns (connection_dict, viewer_is_mentor).
    Fetches connection data from Mentoring Service instead of local DB.
    """
    conns = await _fetch_connections_from_service(user.id)
    if not conns:
        return None, None

    # For dashboard simplicity, pick the first active one
    conn = conns[0]
    
    # Check if the user is mentor or mentee based on their user_id
    # The Mentoring Service returns mentor_id/mentee_id which are PROFILE IDs.
    # We need to map them back to user_ids to know the context.
    
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
        # Verify the connection matches this mentor by user_id
        for c in conns:
            if str(c["mentor_user_id"]) == str(user.id):
                return c, True
    
    if eff == "mentee" and mentee_profile:
        # Verify the connection matches this mentee by user_id
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
        "tier": mp.pricing_tier,
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


async def _active_connection_ids_for_viewer(
    db: Session,
    *,
    user: User,
    viewer_is_mentor: bool,
) -> tuple[list[UUID], MentorProfile | None]:
    conns = await _fetch_connections_from_service(user.id)
    if not conns:
        return [], None
        
    if viewer_is_mentor:
        mp = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
        if not mp:
            return [], None
        # The service already filtered by user_id via header, but we verify by user_id to be safe
        ids = [UUID(str(c["id"])) for c in conns if str(c["mentor_user_id"]) == str(user.id)]
        return ids, mp
    else:
        mep = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
        if not mep:
            return [], None
        ids = [UUID(str(c["id"])) for c in conns if str(c["mentee_user_id"]) == str(user.id)]
        return ids, None


async def _collect_upcoming_payloads(
    db: Session,
    *,
    viewer_is_mentor: bool,
    conn_ids: list[UUID],
    mentor_profile: MentorProfile | None,
    include_rejected_booking_requests: bool,
    max_items: int,
) -> list[dict]:
    """Merge scheduled sessions with pending (and optionally rejected) session booking requests."""
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
            .join(MentorshipConnection, MentorshipConnection.id == SessionBookingRequest.connection_id)
            .filter(
                MentorshipConnection.mentor_id == mentor_profile.id,
                MentorshipConnection.status == "ACTIVE",
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

    events: list[tuple] = []
    for row in sched:
        events.append((row.start_time, "session", row))
    for req, slot in booking_pairs:
        events.append((slot.start_time, "request", (req, slot)))
    events.sort(key=lambda x: x[0])

    out: list[dict] = []
    for _, kind, payload in events:
        if len(out) >= cap:
            break
        if kind == "session":
            row = payload
            # Connection data comes from Mentoring Service via the connection_id in the session
            # We fetch all connections for the user and find the one matching the session
            conns = await _fetch_connections_from_service(user.id)
            sess_conn = next((c for c in conns if str(c["id"]) == str(row.connection_id)), None)
            if not sess_conn:
                continue
                
            partner = _partner_user_for_connection(
                db, sess_conn, viewer_is_mentor=viewer_is_mentor
            )
            price = _session_price_for_row(db, row, sess_conn)
            mentor_brief, mentee_brief = _mentor_mentee_brief(db, sess_conn)
            out.append(
                {
                    "session_id": row.id,
                    "booking_request_id": None,
                    "start_time": row.start_time,
                    "meeting_url": row.meeting_url,
                    "status": row.status,
                    "partner_name": _partner_display_name(partner),
                    "session_credit_cost": price,
                    "price": price,
                    "mentor": mentor_brief,
                    "mentee": mentee_brief,
                }
            )
        else:
            req, slot = payload
            conns = await _fetch_connections_from_service(user.id)
            sess_conn = next((c for c in conns if str(c["id"]) == str(req.connection_id)), None)
            if not sess_conn:
                continue
                
            partner = _partner_user_for_connection(
                db, sess_conn, viewer_is_mentor=viewer_is_mentor
            )
            mentor_brief, mentee_brief = _mentor_mentee_brief(db, sess_conn)
            ui_status = (
                "PENDING_APPROVAL" if req.status == "PENDING" else "REJECTED"
            )
            cost = int(req.agreed_cost)
            out.append(
                {
                    "session_id": None,
                    "booking_request_id": req.id,
                    "start_time": slot.start_time,
                    "meeting_url": None,
                    "status": ui_status,
                    "partner_name": _partner_display_name(partner),
                    "session_credit_cost": cost,
                    "price": cost,
                    "mentor": mentor_brief,
                    "mentee": mentee_brief,
                }
            )
    return out


async def get_upcoming_session(
    db: Session,
    *,
    user: User,
    context: str | None,
) -> dict | None:
    conn, viewer_is_mentor = await resolve_connection(db, user=user, context=context)
    conn_ids, mp = await _active_connection_ids_for_viewer(db, user=user, viewer_is_mentor=bool(viewer_is_mentor))
    if not conn_ids:
        return None

    rows = await _collect_upcoming_payloads(
        db,
        viewer_is_mentor=viewer_is_mentor,
        conn_ids=conn_ids,
        mentor_profile=mp,
        include_rejected_booking_requests=False,
        max_items=1,
    )
    return rows[0] if rows else None


async def get_upcoming_sessions(
    db: Session,
    *,
    user: User,
    context: str | None,
    limit: int = 5,
) -> list[dict]:
    conn, viewer_is_mentor = await resolve_connection(db, user=user, context=context)
    conn_ids, mp = await _active_connection_ids_for_viewer(db, user=user, viewer_is_mentor=bool(viewer_is_mentor))
    if not conn_ids:
        return []

    include_rejected = not viewer_is_mentor
    return await _collect_upcoming_payloads(
        db,
        viewer_is_mentor=viewer_is_mentor,
        conn_ids=conn_ids,
        mentor_profile=mp,
        include_rejected_booking_requests=include_rejected,
        max_items=limit,
    )


async def get_goals(
    db: Session,
    *,
    user: User,
    context: str | None,
) -> list[dict]:
    conn, _ = await resolve_connection(db, user=user, context=context)
    if not conn:
        return []
    
    rows = db.query(Goal).filter(Goal.connection_id == conn.id).all()
    return [{
        "id": g.id,
        "title": g.title,
        "status": g.status,
    } for g in rows]


def _session_duration_hours(db: Session, sess: MentorshipSession) -> float:
    """Use slot window when present; otherwise assume 1 hour."""
    if sess.slot_id:
        slot = db.query(TimeSlot).filter(TimeSlot.id == sess.slot_id).first()
        if slot and slot.start_time and slot.end_time:
            delta = slot.end_time - slot.start_time
            return max(0.0, delta.total_seconds() / 3600.0)
    return 1.0


async def get_dashboard_stats(
    db: Session,
    *,
    user: User,
    context: str | None,
) -> dict:
    # ADMIN GLOBAL VIEW
    if user.is_admin:
        all_conns = await _fetch_admin_all_connections()
        unique_mentors = len(set(str(c["mentor_id"]) for c in all_conns))
        unique_mentees = len(set(str(c["mentee_id"]) for c in all_conns))
        
        return {
            "active_partners": unique_mentors if context != "mentor" else unique_mentees,
            "hours_total": 0.0,
            "hours_this_week": 0.0,
            "sessions_completed": 0,
            "active_sessions": len(all_conns),
        }

    conn_dict, viewer_is_mentor = await resolve_connection(db, user=user, context=context)
    conn_ids, mp = await _active_connection_ids_for_viewer(db, user=user, viewer_is_mentor=bool(viewer_is_mentor))
    
    if not conn_ids:
        return {
            "active_partners": 0,
            "hours_total": 0.0,
            "hours_this_week": 0.0,
            "sessions_completed": 0,
            "active_sessions": 0,
        }

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    hours_total = 0.0
    hours_week = 0.0
    
    completed_rows = (
        db.query(MentorshipSession)
        .filter(
            MentorshipSession.connection_id.in_(conn_ids),
            MentorshipSession.status == "COMPLETED",
        )
        .all()
    )
    sessions_completed = len(completed_rows)
    for s in completed_rows:
        h = _session_duration_hours(db, s)
        hours_total += h
        st = s.start_time
        if st is not None:
            st_aware = st if st.tzinfo else st.replace(tzinfo=timezone.utc)
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


async def get_vault(
    db: Session,
    *,
    user: User,
    context: str | None,
) -> list[dict]:
    conn, viewer_is_mentor = await resolve_connection(db, user=user, context=context)
    if not conn:
        return []
    
    # Mentoring Service handles connection_id mapping
    rows_db = (
        db.query(SessionHistory, MentorshipSession)
        .join(MentorshipSession, MentorshipSession.id == SessionHistory.session_id)
        .filter(MentorshipSession.connection_id == UUID(str(conn["id"])))
        .all()
    )
    
    partner = _partner_user_for_connection(db, conn, viewer_is_mentor=bool(viewer_is_mentor))
    partner_name = _partner_display_name(partner)
    
    rows = []
    for history, session in rows_db:
        rows.append({
            "session_id": session.id,
            "start_time": session.start_time,
            "notes": history.notes_data or {},
            "mentor_rating": history.mentor_rating,
            "mentee_rating": history.mentee_rating,
            "partner_name": partner_name,
        })
    return rows


