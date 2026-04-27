from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


def resolve_connection(
    db: Session,
    *,
    user: User,
    context: str | None,
) -> tuple[MentorshipConnection | None, bool | None]:
    """
    Returns (connection, viewer_is_mentor).
    viewer_is_mentor True means the current user is the mentor on the connection.
    """
    mentor_profile = (
        db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
    )
    mentee_profile = (
        db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    )
    has_mentor = mentor_profile is not None
    has_mentee = mentee_profile is not None

    if context not in (None, "mentor", "mentee"):
        return None, None

    eff = _effective_context(
        context=context,
        has_mentor=has_mentor,
        has_mentee=has_mentee,
    )
    if eff is None:
        return None, None

    if eff == "mentor":
        if not mentor_profile:
            return None, None
        conn = (
            db.query(MentorshipConnection)
            .filter(
                MentorshipConnection.mentor_id == mentor_profile.id,
                MentorshipConnection.status == "ACTIVE",
            )
            .order_by(MentorshipConnection.id.asc())
            .first()
        )
        if not conn:
            return None, None
        return conn, True

    if not mentee_profile:
        return None, None
    conn = (
        db.query(MentorshipConnection)
        .filter(
            MentorshipConnection.mentee_id == mentee_profile.id,
            MentorshipConnection.status == "ACTIVE",
        )
        .order_by(MentorshipConnection.id.asc())
        .first()
    )
    if not conn:
        return None, None
    return conn, False


def _session_price_for_row(
    db: Session,
    row: MentorshipSession,
    sess_conn: MentorshipConnection,
) -> int:
    if row.price_charged is not None:
        return int(row.price_charged)
    mp = (
        db.query(MentorProfile)
        .filter(MentorProfile.id == sess_conn.mentor_id)
        .one()
    )
    return resolve_mentor_session_price(db, mp)


def _mentor_mentee_brief(
    db: Session,
    sess_conn: MentorshipConnection,
) -> tuple[dict, dict]:
    mp = db.query(MentorProfile).filter(MentorProfile.id == sess_conn.mentor_id).one()
    me = db.query(MenteeProfile).filter(MenteeProfile.id == sess_conn.mentee_id).one()
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
    conn: MentorshipConnection,
    *,
    viewer_is_mentor: bool,
) -> User | None:
    if viewer_is_mentor:
        mp = (
            db.query(MenteeProfile)
            .filter(MenteeProfile.id == conn.mentee_id)
            .first()
        )
        if not mp:
            return None
        return db.query(User).filter(User.id == mp.user_id).first()
    mp = (
        db.query(MentorProfile)
        .filter(MentorProfile.id == conn.mentor_id)
        .first()
    )
    if not mp:
        return None
    return db.query(User).filter(User.id == mp.user_id).first()


async def _active_connection_ids_for_viewer(
    db: Session,
    *,
    user: User,
    viewer_is_mentor: bool,
) -> tuple[list, MentorProfile | None]:
    # --- CROSS-SERVICE BRIDGE: Persistent Sync ---
    from app.services.mentoring_client import get_active_connections_from_mentoring_service
    remote_conns = await get_active_connections_from_mentoring_service(user.id)
    if remote_conns:
        conn_ids = []
        for r in remote_conns:
            c_id = uuid.UUID(str(r["id"]))
            conn_ids.append(c_id)
            
            # Sync to local DB so Join-based queries work
            if not db.query(MentorshipConnection).filter(MentorshipConnection.id == c_id).first():
                m_uid = uuid.UUID(str(r["mentor_user_id"]))
                me_uid = uuid.UUID(str(r["mentee_user_id"]))
                
                # Ensure users exist (Shadow Sync)
                if not db.query(User).filter(User.id == m_uid).first():
                    db.add(User(id=m_uid, email=r.get("mentor_email") or f"mentor_{str(m_uid)[:8]}@shadow.com", is_admin=False))
                if not db.query(User).filter(User.id == me_uid).first():
                    db.add(User(id=me_uid, email=r.get("mentee_email") or f"mentee_{str(me_uid)[:8]}@shadow.com", is_admin=False))
                
                # Ensure profiles exist
                if not db.query(MentorProfile).filter(MentorProfile.id == uuid.UUID(str(r["mentor_id"]))).first():
                    db.add(MentorProfile(id=uuid.UUID(str(r["mentor_id"])), user_id=m_uid))
                if not db.query(MenteeProfile).filter(MenteeProfile.id == uuid.UUID(str(r["mentee_id"]))).first():
                    db.add(MenteeProfile(id=uuid.UUID(str(r["mentee_id"])), user_id=me_uid))
                
                # Create connection using LOCAL profile IDs to satisfy FK constraints
                db.add(MentorshipConnection(
                    id=c_id,
                    mentor_id=local_mentor.id,
                    mentee_id=local_mentee.id,
                    status="ACTIVE"
                ))
                db.commit()
                log.info("Dashboard Sync: Created local connection %s for user %s", c_id, user.id)
        
        mp = None
        if viewer_is_mentor:
            mp = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
        return conn_ids, mp
    # --- END BRIDGE ---

    if viewer_is_mentor:
        mp = db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first()
        if not mp:
            return [], None
        conn_ids = [
            r.id
            for r in db.query(MentorshipConnection)
            .filter(
                MentorshipConnection.mentor_id == mp.id,
                MentorshipConnection.status == "ACTIVE",
            )
            .all()
        ]
        return conn_ids, mp
    me = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
    if not me:
        return [], None
    conn_ids = [
        r.id
        for r in db.query(MentorshipConnection)
        .filter(
            MentorshipConnection.mentee_id == me.id,
            MentorshipConnection.status == "ACTIVE",
        )
        .all()
    ]
    return conn_ids, None


async def _collect_upcoming_payloads(
    db: Session,
    *,
    viewer_is_mentor: bool,
    conn_ids: list,
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
            sess_conn = (
                db.query(MentorshipConnection)
                .filter(MentorshipConnection.id == row.connection_id)
                .first()
            )
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
            sess_conn = (
                db.query(MentorshipConnection)
                .filter(MentorshipConnection.id == req.connection_id)
                .first()
            )
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
    conn, viewer_is_mentor = resolve_connection(db, user=user, context=context)
    # Note: resolve_connection is sync but we mainly need viewer_is_mentor
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
    """
    Next N upcoming items: scheduled sessions plus session booking requests (pending; mentee list also rejected).
    """
    conn, viewer_is_mentor = resolve_connection(db, user=user, context=context)
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
    conn, _ = resolve_connection(db, user=user, context=context)
    # --- CROSS-SERVICE BRIDGE ---
    from app.services.mentoring_client import get_goals_from_mentoring_service
    # If we have a local connection use it, otherwise we could try to find one from the remote bridge
    if not conn:
        from app.services.mentoring_client import get_active_connections_from_mentoring_service
        remotes = await get_active_connections_from_mentoring_service(user.id)
        if remotes:
            return await get_goals_from_mentoring_service(uuid.UUID(str(remotes[0]["id"])))
        return []
    
    return await get_goals_from_mentoring_service(conn.id)


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
    conn, viewer_is_mentor = resolve_connection(db, user=user, context=context)
    conn_ids, mp = await _active_connection_ids_for_viewer(db, user=user, viewer_is_mentor=bool(viewer_is_mentor))
    
    # --- CROSS-SERVICE BRIDGE: ADMIN GLOBAL VIEW ---
    if user.is_admin:
        from app.services.mentoring_client import get_admin_connections_from_mentoring_service
        all_conns = await get_admin_connections_from_mentoring_service()
        unique_mentors = len(set(str(c["mentor_id"]) for c in all_conns))
        unique_mentees = len(set(str(c["mentee_id"]) for c in all_conns))
        
        # Admin sees global counts
        return {
            "active_partners": unique_mentors if context != "mentor" else unique_mentees,
            "hours_total": 0.0,
            "hours_this_week": 0.0,
            "sessions_completed": 0,
            "active_sessions": len(all_conns),
        }
    
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

    # --- CROSS-SERVICE BRIDGE: Session History ---
    from app.services.mentoring_client import get_session_history_from_mentoring_service
    # We fetch for all active connection IDs
    history_rows = []
    for c_id in conn_ids:
        remote_history = await get_session_history_from_mentoring_service(c_id)
        history_rows.extend(remote_history)
    
    hours_total = 0.0
    hours_week = 0.0
    sessions_completed = 0
    
    for h_row in history_rows:
        # Expected keys: duration_hours, start_time
        sessions_completed += 1
        h = float(h_row.get("duration_hours", 1.0))
        hours_total += h
        st_str = h_row.get("start_time")
        if st_str:
            try:
                st = datetime.fromisoformat(st_str.replace("Z", "+00:00"))
                if st >= week_ago:
                    hours_week += h
            except Exception:
                pass

    active_ct = (
        db.query(MentorshipSession)
        .filter(
            MentorshipSession.connection_id.in_(conn_ids),
            MentorshipSession.status == "SCHEDULED",
        )
        .count()
    )
    
    # Fallback to local if bridge is empty (migration period)
    if not history_rows:
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
    conn, viewer_is_mentor = resolve_connection(db, user=user, context=context)
    # --- CROSS-SERVICE BRIDGE ---
    from app.services.mentoring_client import get_vault_from_mentoring_service
    if not conn:
        from app.services.mentoring_client import get_active_connections_from_mentoring_service
        remotes = await get_active_connections_from_mentoring_service(user.id)
        if not remotes:
            return []
        conn_id = uuid.UUID(str(remotes[0]["id"]))
    else:
        conn_id = conn.id

    rows = await get_vault_from_mentoring_service(conn_id)
    # Enrich with partner names from local DB if possible
    partner = None
    if conn:
        partner = _partner_user_for_connection(db, conn, viewer_is_mentor=bool(viewer_is_mentor))
    
    for r in rows:
        r["partner_name"] = _partner_display_name(partner)
    return rows
