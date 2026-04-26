import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

from app.auth import hash_password
from app.db import Base, SessionLocal, engine
from app.models import (
    AdminProfile,
    CreditLedgerEntry,
    Goal,
    MenteeProfile,
    MentorProfile,
    MentorshipConnection,
    MentorshipRequest,
    ReportDispute,
    SessionHistory,
    TimeSlot,
    User,
)
from app.models import Session as MentorshipSession


def _allowed_seed_emails() -> frozenset[str]:
    """Users kept when pruning the DB before re-seeding (admin + 10 mentors + 10 mentees)."""
    return frozenset(
        {"admin@test.com"}
        | {f"mentor_{i}@test.com" for i in range(1, 11)}
        | {f"mentee_{i}@test.com" for i in range(1, 11)}
    )


def _mentee_seed_wallet_target(index: int) -> int:
    """User-service mirror + gamification top-up target for mentee_{index}@test.com."""
    if 1 <= index <= 5:
        return 200
    if 6 <= index <= 10:
        return 500
    return 500


def run_seed_all(*, force_dashboard: bool = False) -> None:
    """
    Create tables, seed test users, profiles, and dashboard dummy rows.

    Primary test identities: mentor_1..mentor_10 and mentee_1..mentee_10 @test.com (password123),
    plus admin@test.com.

    **Any other user row** (e.g. legacy mentor@test.com, old manual seeds, aisha@test.com, etc.)
    is **removed** at the start of each seed run so only the allowlist accounts remain.

    Use force_dashboard=True to wipe and re-insert sessions/goals/vault for the
    mentor_1@test.com ↔ mentee_1@test.com connection.
    """
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # purge_users_not_in_seed_allowlist(db)
        ensure_seed_users(db)
        ensure_admin_user(db)
        ensure_seed_profiles(db)
        ensure_seed_connections(db)
        ensure_dashboard_seed(db, force=force_dashboard)
        bump_mentee_test_wallets(db)
        ensure_mentee_credit_service_floor_all(db)
        ensure_time_slots_for_demo_mentor(db)
        ensure_time_slots_for_seed_mentors(db)
        ensure_slot_costs_for_booking_demo(db)
        ensure_mentees_welcome_balance(db)
        ensure_sample_dispute(db)
    finally:
        db.close()


def seed_if_empty() -> None:
    run_seed_all(force_dashboard=False)


def _delete_user_and_dependents(db: Session, user_id: UUID) -> None:
    """
    Remove a user and FK-linked rows in safe order.

    Plain ``db.delete(user)`` can make SQLAlchemy emit ``UPDATE mentee_profiles SET user_id=NULL``,
    which violates NOT NULL — so we delete profiles and graph explicitly.
    """
    mp = db.query(MentorProfile).filter(MentorProfile.user_id == user_id).first()
    mep = db.query(MenteeProfile).filter(MenteeProfile.user_id == user_id).first()

    if mp or mep:
        conds = []
        if mp:
            conds.append(MentorshipRequest.mentor_id == mp.id)
        if mep:
            conds.append(MentorshipRequest.mentee_id == mep.id)
        if conds:
            db.query(MentorshipRequest).filter(or_(*conds)).delete(synchronize_session=False)

    if mp or mep:
        c_conds = []
        if mp:
            c_conds.append(MentorshipConnection.mentor_id == mp.id)
        if mep:
            c_conds.append(MentorshipConnection.mentee_id == mep.id)
        conns = db.query(MentorshipConnection).filter(or_(*c_conds)).all()
        for conn in conns:
            sess_rows = (
                db.query(MentorshipSession)
                .filter(MentorshipSession.connection_id == conn.id)
                .all()
            )
            for srow in sess_rows:
                db.query(SessionHistory).filter(SessionHistory.session_id == srow.id).delete(
                    synchronize_session=False
                )
                db.query(ReportDispute).filter(ReportDispute.session_id == srow.id).delete(
                    synchronize_session=False
                )
            db.query(MentorshipSession).filter(
                MentorshipSession.connection_id == conn.id
            ).delete(synchronize_session=False)
            db.query(Goal).filter(Goal.connection_id == conn.id).delete(synchronize_session=False)
        if conns:
            db.query(MentorshipConnection).filter(
                MentorshipConnection.id.in_([c.id for c in conns])
            ).delete(synchronize_session=False)

    if mp:
        db.query(TimeSlot).filter(TimeSlot.mentor_id == mp.id).delete(synchronize_session=False)
        db.query(MentorProfile).filter(MentorProfile.id == mp.id).delete(synchronize_session=False)
    if mep:
        db.query(MenteeProfile).filter(MenteeProfile.id == mep.id).delete(synchronize_session=False)

    db.query(CreditLedgerEntry).filter(CreditLedgerEntry.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(ReportDispute).filter(ReportDispute.opened_by_user_id == user_id).delete(
        synchronize_session=False
    )

    ap = db.query(AdminProfile).filter(AdminProfile.user_id == user_id).first()
    if ap:
        db.query(AdminProfile).filter(AdminProfile.user_id == user_id).delete(
            synchronize_session=False
        )

    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)


def purge_users_not_in_seed_allowlist(db: Session) -> None:
    """
    Delete every user not in the canonical seed allowlist (admin + mentor_1..10 + mentee_1..10).

    Removes prior demo data, one-off test accounts, and old seed identities in one pass.
    """
    allowed = _allowed_seed_emails()
    extras = db.query(User).filter(~User.email.in_(allowed)).all()
    for u in extras:
        _delete_user_and_dependents(db, u.id)
    db.commit()


def _seed_emails() -> list[str]:
    mentors = [f"mentor_{i}@test.com" for i in range(1, 11)]
    mentees = [f"mentee_{i}@test.com" for i in range(1, 11)]
    return mentors + mentees


def ensure_seed_users(db: Session) -> None:
    """Idempotent: ensure seeded test accounts exist (keeps passwords stable for dev)."""
    for email in _seed_emails():
        u = db.query(User).filter(User.email == email).first()
        if not u:
            db.add(User(email=email, password_hash=hash_password("password123")))
    db.commit()


def ensure_admin_user(db: Session) -> None:
    """
    Ensure admin@test.com exists with is_admin=true (RBAC) and optional admin_profiles row.

    Dev password defaults to "password" when USERSERVICE_RESET_ADMIN_PASSWORD is true.
    """
    reset_pw = os.getenv("USERSERVICE_RESET_ADMIN_PASSWORD", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    u = db.query(User).filter(User.email == "admin@test.com").first()
    if not u:
        u = User(
            email="admin@test.com",
            password_hash=hash_password("password"),
            is_admin=True,
        )
        db.add(u)
        db.flush()
    else:
        u.is_admin = True
        if reset_pw:
            u.password_hash = hash_password("password")

    if not db.query(AdminProfile).filter(AdminProfile.user_id == u.id).first():
        db.add(AdminProfile(user_id=u.id))

    db.commit()


def ensure_seed_profiles(db: Session) -> None:
    """Idempotent: mentor_1..10 and mentee_1..10 profiles for scheduling and admin demos."""
    for i in range(1, 11):
        email = f"mentor_{i}@test.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            continue
        if not db.query(MentorProfile).filter(MentorProfile.user_id == user.id).first():
            tracks = [
                ["React", "TypeScript", "Frontend architecture"],
                ["Python", "FastAPI", "Backend APIs"],
                ["System design", "Distributed systems", "Scaling"],
                ["Data science", "Pandas", "ML basics"],
                ["DevOps", "Docker", "Kubernetes"],
                ["Android", "Kotlin", "Mobile"],
                ["Product management", "Roadmaps", "Stakeholder mgmt"],
                ["UI/UX", "Design systems", "Figma"],
                ["Security", "OWASP", "Threat modeling"],
                ["Career coaching", "Interview prep", "Resume"],
            ]
            areas = tracks[(i - 1) % len(tracks)]
            db.add(
                MentorProfile(
                    user_id=user.id,
                    tier_id="PROFESSIONAL",
                    pricing_tier="TIER_2",
                    is_accepting_requests=True,
                    expertise_areas=[*areas, "Mentoring"],
                    total_hours_mentored=10 * i,
                    headline=f"{areas[0]} mentor • {areas[1]} • {areas[2]}",
                    bio=(
                        f"I help mentees grow in {areas[0]} and {areas[1]} with practical projects and clear feedback. "
                        f"Best for learners aiming to improve {areas[2].lower()}."
                    ),
                    current_title=f"Senior {areas[0]} Engineer",
                    current_company=f"Company {i}",
                    years_experience=2 + i,
                    professional_experiences=[
                        {
                            "title": f"{areas[0]} Engineer",
                            "company": f"Company {i}",
                            "years": max(1, (2 + i) // 2),
                            "summary": f"Built and shipped features in {areas[1]} and {areas[2]}.",
                        },
                        {
                            "title": f"Mentor / Coach",
                            "company": "Community",
                            "years": 1,
                            "summary": "Ran weekly sessions, code reviews, and interview practice.",
                        },
                    ],
                )
            )

    for i in range(1, 11):
        email = f"mentee_{i}@test.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            continue
        if not db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first():
            db.add(
                MenteeProfile(
                    user_id=user.id,
                    learning_goals=[f"Learning goal {i}", "Skill growth"],
                    education_level="Undergraduate",
                    is_minor=False,
                    guardian_consent_status="NOT_REQUIRED",
                    cached_credit_score=_mentee_seed_wallet_target(i),
                )
            )

    db.commit()


def ensure_seed_connections(db: Session) -> None:
    """
    One ACTIVE connection per index: mentee_i ↔ mentor_i (i = 1..10).
    """
    desired: list[tuple] = []
    for i in range(1, 11):
        mu = db.query(User).filter(User.email == f"mentor_{i}@test.com").first()
        meu = db.query(User).filter(User.email == f"mentee_{i}@test.com").first()
        if not mu or not meu:
            continue
        mp = db.query(MentorProfile).filter(MentorProfile.user_id == mu.id).first()
        mep = db.query(MenteeProfile).filter(MenteeProfile.user_id == meu.id).first()
        if not mp or not mep:
            continue
        desired.append((mep.id, mp.id))

    for mentee_id, mentor_id in desired:
        row = (
            db.query(MentorshipConnection)
            .filter(
                MentorshipConnection.mentee_id == mentee_id,
                MentorshipConnection.mentor_id == mentor_id,
            )
            .first()
        )
        if not row:
            db.add(
                MentorshipConnection(
                    mentee_id=mentee_id,
                    mentor_id=mentor_id,
                    status="ACTIVE",
                )
            )
        elif row.status != "ACTIVE":
            row.status = "ACTIVE"
    db.commit()


def bump_mentee_test_wallets(db: Session) -> None:
    """Sync mentee_1..10 cached_credit_score to seed targets (200 for 1–5, 500 for 6–10)."""
    for i in range(1, 11):
        target = _mentee_seed_wallet_target(i)
        user = db.query(User).filter(User.email == f"mentee_{i}@test.com").first()
        if not user:
            continue
        prof = db.query(MenteeProfile).filter(MenteeProfile.user_id == user.id).first()
        if not prof:
            continue
        old = int(prof.cached_credit_score)
        if old == target:
            continue
        prof.cached_credit_score = target
        db.add(
            CreditLedgerEntry(
                user_id=user.id,
                delta=target - old,
                balance_after=target,
                reason="Demo wallet top-up (dev seed)",
            )
        )
    db.commit()


def ensure_mentee_credit_service_floor_all(db: Session) -> None:
    """
    When GAMIFICATION_SERVICE_URL is set, top up each mentee's gamification wallet to the seed target:
    mentee_1..5 → 200 credits, mentee_6..10 → 500 credits (idempotent; uses /add only).
    """
    url = os.getenv("GAMIFICATION_SERVICE_URL", "").strip().rstrip("/")
    if not url:
        return
    for i in range(1, 11):
        target = _mentee_seed_wallet_target(i)
        user = db.query(User).filter(User.email == f"mentee_{i}@test.com").first()
        if not user:
            continue
        try:
            r = httpx.get(f"{url}/balance/{user.id}", timeout=10.0)
            if r.status_code != 200:
                log.warning("credit floor: balance GET %s", r.status_code)
                continue
            bal = int(r.json().get("balance", 0))
            need = max(0, target - bal)
            if need <= 0:
                log.info(
                    "gamification wallet OK mentee_%s user_id=%s balance=%s (target=%s)",
                    i,
                    user.id,
                    bal,
                    target,
                )
                continue
            a = httpx.post(
                f"{url}/add",
                json={"user_id": str(user.id), "amount": need, "xp": 0},
                timeout=15.0,
            )
            if a.status_code != 200:
                log.warning("credit floor: add POST %s %s", a.status_code, a.text[:200])
            else:
                try:
                    new_bal = a.json().get("balance", need + bal)
                except Exception:  # noqa: BLE001
                    new_bal = "?"
                log.info(
                    "gamification wallet topped up mentee_%s user_id=%s added=%s balance=%s (target=%s)",
                    i,
                    user.id,
                    need,
                    new_bal,
                    target,
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("credit floor sync skipped for mentee_%s: %s", i, exc)


def ensure_time_slots_for_demo_mentor(db: Session) -> None:
    """Open bookable slots for mentor_1@test.com (primary scheduling demo)."""
    mentor_user = db.query(User).filter(User.email == "mentor_1@test.com").first()
    if not mentor_user:
        return
    mp = db.query(MentorProfile).filter(MentorProfile.user_id == mentor_user.id).first()
    if not mp:
        return
    if db.query(TimeSlot).filter(TimeSlot.mentor_id == mp.id).count() > 0:
        return
    now = datetime.now(timezone.utc)
    slots: list[TimeSlot] = []
    for day in (7, 8, 9, 10):
        start = now + timedelta(days=day)
        end = start + timedelta(hours=1)
        slots.append(
            TimeSlot(
                mentor_id=mp.id,
                start_time=start,
                end_time=end,
                is_booked=False,
                cost_credits=5,
            )
        )
    db.add_all(slots)
    db.commit()


def ensure_time_slots_for_seed_mentors(db: Session) -> None:
    """
    Many open 1h slots (UTC) for mentor_1@test.com … mentor_10@test.com.

    Idempotent on (mentor_id, start_time). Skips start times already in the past.
    """
    now = datetime.now(timezone.utc)
    hours_each_day = (8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20)
    mentor_emails = [f"mentor_{i}@test.com" for i in range(1, 11)]
    for day_offset in range(1, 11):
        day = now.date() + timedelta(days=day_offset)
        for hour in hours_each_day:
            start = datetime(
                day.year, day.month, day.day, hour, 0, tzinfo=timezone.utc
            )
            if start <= now:
                continue
            end = start + timedelta(hours=1)
            for email in mentor_emails:
                u = db.query(User).filter(User.email == email).first()
                if not u:
                    continue
                mp = db.query(MentorProfile).filter(MentorProfile.user_id == u.id).first()
                if not mp:
                    continue
                exists = (
                    db.query(TimeSlot)
                    .filter(
                        TimeSlot.mentor_id == mp.id,
                        TimeSlot.start_time == start,
                    )
                    .first()
                )
                if exists:
                    continue
                db.add(
                    TimeSlot(
                        mentor_id=mp.id,
                        start_time=start,
                        end_time=end,
                        is_booked=False,
                        cost_credits=25,
                    )
                )
    db.commit()


def ensure_slot_costs_for_booking_demo(db: Session) -> None:
    """Ensure demo mentors' slots have a non-zero coin cost (existing rows may be 0)."""
    for email in [f"mentor_{i}@test.com" for i in range(1, 11)]:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            continue
        mp = db.query(MentorProfile).filter(MentorProfile.user_id == u.id).first()
        if not mp:
            continue
        db.query(TimeSlot).filter(
            TimeSlot.mentor_id == mp.id,
            TimeSlot.cost_credits == 0,
        ).update({TimeSlot.cost_credits: 25}, synchronize_session=False)
    db.commit()


def ensure_mentees_welcome_balance(db: Session) -> None:
    """Dev/demo: non-seed mentees with zero balance get 100 (seed mentee_1..10 use tiered targets)."""
    seed_mentee_emails = {f"mentee_{i}@test.com" for i in range(1, 11)}
    q = (
        db.query(MenteeProfile)
        .join(User, User.id == MenteeProfile.user_id)
        .filter(MenteeProfile.cached_credit_score == 0)
        .filter(~User.email.in_(seed_mentee_emails))
    )
    for p in q.all():
        p.cached_credit_score = 100
        db.add(
            CreditLedgerEntry(
                user_id=p.user_id,
                delta=100,
                balance_after=100,
                reason="Welcome bonus (dev seed)",
            )
        )
    db.commit()


def ensure_sample_dispute(db: Session) -> None:
    """One OPEN dispute for admin UI demos when sessions exist."""
    if db.query(ReportDispute).count() > 0:
        return
    mentee_user = db.query(User).filter(User.email == "mentee_1@test.com").first()
    if not mentee_user:
        return
    sess = db.query(MentorshipSession).filter(MentorshipSession.status == "COMPLETED").first()
    if not sess:
        return
    db.add(
        ReportDispute(
            status="OPEN",
            kind="NO_SHOW",
            session_id=sess.id,
            opened_by_user_id=mentee_user.id,
            payload={"note": "Demo dispute for admin resolution"},
        )
    )
    db.commit()


def ensure_dashboard_seed(db: Session, *, force: bool = False) -> None:
    """
    Idempotent: one ACTIVE mentorship between mentor_1@test.com and mentee_1@test.com
    with sessions, goals, and vault history for dashboard widgets.

    If force=True, removes existing sessions/goals/history for that connection and re-seeds.
    """
    mentor_user = db.query(User).filter(User.email == "mentor_1@test.com").first()
    mentee_user = db.query(User).filter(User.email == "mentee_1@test.com").first()
    if not mentor_user or not mentee_user:
        return

    mentor_profile = (
        db.query(MentorProfile).filter(MentorProfile.user_id == mentor_user.id).first()
    )
    mentee_profile = (
        db.query(MenteeProfile).filter(MenteeProfile.user_id == mentee_user.id).first()
    )
    if not mentor_profile or not mentee_profile:
        return

    conn = (
        db.query(MentorshipConnection)
        .filter(
            MentorshipConnection.mentor_id == mentor_profile.id,
            MentorshipConnection.mentee_id == mentee_profile.id,
        )
        .first()
    )
    if not conn:
        conn = MentorshipConnection(
            mentor_id=mentor_profile.id,
            mentee_id=mentee_profile.id,
            status="ACTIVE",
        )
        db.add(conn)
        db.commit()
        db.refresh(conn)

    has_sessions = (
        db.query(MentorshipSession)
        .filter(MentorshipSession.connection_id == conn.id)
        .count()
    )
    if has_sessions > 0 and not force:
        return

    if force and has_sessions > 0:
        session_ids = [
            r.id
            for r in db.query(MentorshipSession)
            .filter(MentorshipSession.connection_id == conn.id)
            .all()
        ]
        if session_ids:
            db.query(SessionHistory).filter(
                SessionHistory.session_id.in_(session_ids)
            ).delete(synchronize_session=False)
            db.query(ReportDispute).filter(
                ReportDispute.session_id.in_(session_ids)
            ).delete(synchronize_session=False)
        db.query(MentorshipSession).filter(
            MentorshipSession.connection_id == conn.id
        ).delete(synchronize_session=False)
        db.query(Goal).filter(Goal.connection_id == conn.id).delete(
            synchronize_session=False
        )
        db.commit()

    now = datetime.now(timezone.utc)
    s1 = MentorshipSession(
        connection_id=conn.id,
        start_time=now + timedelta(days=1, hours=2),
        status="SCHEDULED",
        meeting_url="https://meet.example.com/mentor-mentee-a",
    )
    s2 = MentorshipSession(
        connection_id=conn.id,
        start_time=now + timedelta(days=3, hours=4),
        status="SCHEDULED",
        meeting_url="https://meet.example.com/mentor-mentee-b",
    )
    s_done = MentorshipSession(
        connection_id=conn.id,
        start_time=now - timedelta(days=5),
        status="COMPLETED",
        meeting_url="https://meet.example.com/past-session",
    )
    db.add_all([s1, s2, s_done])
    db.flush()

    db.add(
        SessionHistory(
            session_id=s_done.id,
            notes_data={
                "summary": "Career roadmap and skill gaps",
                "highlights": [
                    "Discussed promotion path",
                    "Identified two focus areas",
                ],
            },
            mentor_rating=5,
            mentee_rating=4,
        )
    )
    db.add_all(
        [
            Goal(
                connection_id=conn.id,
                title="Learn Python testing patterns",
                status="ACTIVE",
            ),
            Goal(
                connection_id=conn.id,
                title="Ship a portfolio project",
                status="ACTIVE",
            ),
        ]
    )
    db.commit()


if __name__ == "__main__":
    import sys

    _force = "--force" in sys.argv
    run_seed_all(force_dashboard=_force)
    print(
        "Seed complete."
        + (" (dashboard dummy data refreshed)" if _force else "")
    )
