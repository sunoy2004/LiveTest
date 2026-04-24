import asyncio
import os
import random
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import bcrypt
import sqlalchemy as sa
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import (
    Goal,
    GuardianConsentStatus,
    MenteeProfile,
    MentorshipConnection,
    MentorshipConnectionStatus,
    MentorshipRequest,
    MentorshipRequestStatus,
    MentorProfile,
    MentorTier,
    Session,
    SessionHistory,
    TimeSlot,
)
from app.models.enums import GoalStatus, SessionStatus


@dataclass(frozen=True)
class DualRoleUser:
    user_id: uuid.UUID
    full_name: str


def _rng() -> random.Random:
    seed = os.getenv("LINK_SEED_RANDOM_SEED")
    return random.Random(int(seed)) if seed and seed.isdigit() else random.Random()


def _clean_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in re.split(r"\s+", (full_name or "").strip()) if p]
    first = (parts[0] if parts else "user").lower()
    last = (parts[-1] if len(parts) > 1 else first).lower()
    first = re.sub(r"[^a-z0-9]", "", first) or "user"
    last = re.sub(r"[^a-z0-9]", "", last) or first
    return first, last


def _userservice_db_url() -> str:
    """
    User Service auth lives in users_db (docker compose).
    Allow override via USERSERVICE_DATABASE_URL; otherwise derive from mentoring DATABASE_URL.
    """
    override = os.getenv("USERSERVICE_DATABASE_URL")
    if override and override.strip():
        return override.strip()

    u = urlsplit(settings.database_url)
    # replace last path segment with users_db
    path = u.path or ""
    parts = [p for p in path.split("/") if p]
    if parts:
        parts[-1] = "users_db"
    else:
        parts = ["users_db"]
    new_path = "/" + "/".join(parts)
    return urlunsplit((u.scheme, u.netloc, new_path, u.query, u.fragment))


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


async def _ensure_userservice_accounts(users: list[DualRoleUser]) -> list[tuple[str, str, str]]:
    """
    Create missing accounts in User Service DB so sign-in works.
    Returns rows: (full_name, email, password) for documentation.
    """
    url = _userservice_db_url()
    engine = create_async_engine(url, pool_pre_ping=True)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created_or_existing: list[tuple[str, str, str]] = []
    async with sf() as session:
        async with session.begin():
            for u in users:
                first, last = _clean_name(u.full_name)
                email = f"{first}@test.com"
                password = f"pass{last}"
                exists = await session.scalar(
                    sa.text("select 1 from users where email = :email limit 1").bindparams(email=email)
                )
                if exists is None:
                    await session.execute(
                        sa.text(
                            "insert into users (id, email, password_hash, is_admin) values (:id, :email, :ph, false)"
                        ),
                        {"id": str(uuid.uuid4()), "email": email, "ph": _hash_password(password)},
                    )
                created_or_existing.append((u.full_name, email, password))

    await engine.dispose()
    return created_or_existing


async def _ensure_userservice_profiles(
    *,
    mentors: list[DualRoleUser],
    mentees: list[DualRoleUser],
    rng: random.Random,
) -> None:
    """
    Ensure users_db has mentor_profiles / mentee_profiles for the generated sign-in accounts.
    Scheduling dropdown requires mentee_profiles row for the logged-in user.
    """
    url = _userservice_db_url()
    engine = create_async_engine(url, pool_pre_ping=True)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sf() as session:
        async with session.begin():
            # Ensure tiers exist (user-service expects these)
            await session.execute(
                sa.text(
                    """
                    insert into mentor_tiers (tier_id, tier_name, session_credit_cost)
                    values
                      ('PEER','Peer',50),
                      ('PROFESSIONAL','Professional',100),
                      ('EXPERT','Expert',250)
                    on conflict (tier_id) do nothing
                    """
                )
            )

            tier_ids = ["PEER", "PROFESSIONAL", "EXPERT"]

            # Mentor profiles
            for u in mentors:
                first, _last = _clean_name(u.full_name)
                email = f"{first}@test.com"
                user_id = await session.scalar(
                    sa.text("select id from users where email = :email limit 1").bindparams(email=email)
                )
                if user_id is None:
                    continue
                exists = await session.scalar(
                    sa.text("select 1 from mentor_profiles where user_id = :uid limit 1").bindparams(uid=user_id)
                )
                if exists is None:
                    await session.execute(
                        sa.text(
                            """
                            insert into mentor_profiles
                              (id, user_id, tier_id, is_accepting_requests, expertise_areas, total_hours_mentored)
                            values
                              (:id, :uid, :tier, true, :areas, 0)
                            """
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "uid": user_id,
                            "tier": rng.choice(tier_ids),
                            "areas": [],
                        },
                    )

            # Mentee profiles
            for u in mentees:
                first, _last = _clean_name(u.full_name)
                email = f"{first}@test.com"
                user_id = await session.scalar(
                    sa.text("select id from users where email = :email limit 1").bindparams(email=email)
                )
                if user_id is None:
                    continue
                exists = await session.scalar(
                    sa.text("select 1 from mentee_profiles where user_id = :uid limit 1").bindparams(uid=user_id)
                )
                if exists is None:
                    await session.execute(
                        sa.text(
                            """
                            insert into mentee_profiles
                              (id, user_id, learning_goals, education_level, is_minor, guardian_consent_status, cached_credit_score)
                            values
                              (:id, :uid, :goals, 'UNDERGRAD', false, 'NOT_REQUIRED', 500)
                            """
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "uid": user_id,
                            "goals": [],
                        },
                    )

    await engine.dispose()


async def _seed_userservice_connections_and_slots(
    *,
    rng: random.Random,
    target_connections: int = 5,
) -> list[tuple[str, str, str]]:
    """
    Ensure users_db has ACTIVE mentorship_connections + bookable time_slots so
    ScheduleSessionDialog dropdown + availability work.

    Returns connection rows for docs: (mentor_name, mentee_name, status).
    """
    url = _userservice_db_url()
    engine = create_async_engine(url, pool_pre_ping=True)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sf() as session:
        async with session.begin():
            mentor_rows = (
                await session.execute(
                    sa.text(
                        """
                        select mp.id as mentor_id, u.email as mentor_email
                        from mentor_profiles mp
                        join users u on u.id = mp.user_id
                        order by u.email asc
                        """
                    )
                )
            ).all()
            mentee_rows = (
                await session.execute(
                    sa.text(
                        """
                        select me.id as mentee_id, u.email as mentee_email
                        from mentee_profiles me
                        join users u on u.id = me.user_id
                        order by u.email asc
                        """
                    )
                )
            ).all()

            existing_pairs = set(
                (
                    await session.execute(
                        sa.text("select mentee_id, mentor_id from mentorship_connections")
                    )
                ).all()
            )

            # Choose unique mentors + mentees.
            mentors = list(mentor_rows)
            mentees = list(mentee_rows)
            rng.shuffle(mentors)
            rng.shuffle(mentees)

            created = 0
            used_mentor_ids: set[str] = set()

            # First, guarantee every mentee has at least one ACTIVE connection.
            for mentee_id, mentee_email in mentees:
                has_any = (mentee_id, )  # marker
                # check existence (any mentor) for this mentee
                exists = await session.scalar(
                    sa.text(
                        "select 1 from mentorship_connections where mentee_id = :mid and status='ACTIVE' limit 1"
                    ).bindparams(mid=mentee_id)
                )
                if exists is not None:
                    continue
                # pick a mentor and create a connection
                mentor_id, _mentor_email = rng.choice(mentors)
                if str(mentor_id) == str(mentee_id):
                    continue
                pair = (mentee_id, mentor_id)
                if pair in existing_pairs:
                    continue
                await session.execute(
                    sa.text(
                        """
                        insert into mentorship_connections (id, mentee_id, mentor_id, status)
                        values (:id, :mentee_id, :mentor_id, 'ACTIVE')
                        """
                    ),
                    {"id": str(uuid.uuid4()), "mentee_id": mentee_id, "mentor_id": mentor_id},
                )
                existing_pairs.add(pair)
                used_mentor_ids.add(str(mentor_id))

            # Then, create additional random unique connections up to target_connections (best effort).
            attempts = 0
            while created < target_connections and attempts < 500:
                attempts += 1
                mentor_id, _mentor_email = rng.choice(mentors)
                mentee_id, _mentee_email = rng.choice(mentees)
                if str(mentor_id) == str(mentee_id):
                    continue
                pair = (mentee_id, mentor_id)
                if pair in existing_pairs:
                    continue
                await session.execute(
                    sa.text(
                        """
                        insert into mentorship_connections (id, mentee_id, mentor_id, status)
                        values (:id, :mentee_id, :mentor_id, 'ACTIVE')
                        """
                    ),
                    {"id": str(uuid.uuid4()), "mentee_id": mentee_id, "mentor_id": mentor_id},
                )
                existing_pairs.add(pair)
                used_mentor_ids.add(str(mentor_id))
                created += 1

            # Ensure 2 future unbooked slots per mentor used in connections.
            mentor_ids_used = list(used_mentor_ids)
            now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
            for idx, mid in enumerate(mentor_ids_used):
                count_future = await session.scalar(
                    sa.text(
                        """
                        select count(*) from time_slots
                        where mentor_id = CAST(:mid AS uuid) and start_time >= :now
                        """
                    ).bindparams(mid=mid, now=now)
                )
                need = max(0, 2 - int(count_future or 0))
                for j in range(need):
                    start = now + timedelta(days=idx + 1, hours=j * 2)
                    end = start + timedelta(minutes=30)
                    await session.execute(
                        sa.text(
                            """
                            insert into time_slots (id, mentor_id, start_time, end_time, is_booked, cost_credits)
                            values (:id, CAST(:mid AS uuid), :st, :et, false, 25)
                            """
                        ),
                        {"id": str(uuid.uuid4()), "mid": mid, "st": start, "et": end},
                    )

        # Read connections for docs (active only, joined to emails for display names)
        rows = (
            await session.execute(
                sa.text(
                    """
                    select mu.email as mentor_email, meu.email as mentee_email, c.status
                    from mentorship_connections c
                    join mentor_profiles mp on mp.id = c.mentor_id
                    join users mu on mu.id = mp.user_id
                    join mentee_profiles me on me.id = c.mentee_id
                    join users meu on meu.id = me.user_id
                    order by mu.email asc, meu.email asc
                    """
                )
            )
        ).all()

    await engine.dispose()

    def disp(email: str | None) -> str:
        if not email:
            return "Unknown"
        return email.split("@")[0].replace(".", " ").replace("_", " ").title()

    return [(disp(m), disp(me), str(st)) for m, me, st in rows]


async def _ensure_tiers(session: AsyncSession) -> None:
    existing = (await session.scalars(select(MentorTier.tier_id))).all()
    if existing:
        return
    session.add_all(
        [
            MentorTier(tier_id="PEER", tier_name="Peer", session_credit_cost=50),
            MentorTier(tier_id="PROFESSIONAL", tier_name="Professional", session_credit_cost=100),
            MentorTier(tier_id="EXPERT", tier_name="Expert", session_credit_cost=250),
        ]
    )
    await session.flush()


async def _fetch_profiles(session: AsyncSession) -> tuple[list[MentorProfile], list[MenteeProfile]]:
    mentors = (await session.scalars(select(MentorProfile).limit(10))).all()
    mentees = (await session.scalars(select(MenteeProfile).limit(10))).all()
    return mentors, mentees


async def _ensure_dual_role_users(
    session: AsyncSession,
    mentors: list[MentorProfile],
    mentees: list[MenteeProfile],
    rng: random.Random,
) -> list[DualRoleUser]:
    mentor_by_user = {m.user_id: m for m in mentors}
    mentee_by_user = {m.user_id: m for m in mentees}

    both_user_ids = list(set(mentor_by_user.keys()) & set(mentee_by_user.keys()))
    rng.shuffle(both_user_ids)

    chosen_user_ids: list[uuid.UUID] = both_user_ids[:3]
    if len(chosen_user_ids) < 3:
        # Backfill by selecting from either side and creating the missing profile.
        candidates = list(dict.fromkeys(list(mentor_by_user.keys()) + list(mentee_by_user.keys())))
        rng.shuffle(candidates)
        for uid in candidates:
            if uid in chosen_user_ids:
                continue
            chosen_user_ids.append(uid)
            if len(chosen_user_ids) == 3:
                break

    await _ensure_tiers(session)
    tier_ids = (await session.scalars(select(MentorTier.tier_id))).all() or ["PEER"]

    duals: list[DualRoleUser] = []
    for uid in chosen_user_ids:
        mentor = mentor_by_user.get(uid) or await session.scalar(select(MentorProfile).where(MentorProfile.user_id == uid))
        mentee = mentee_by_user.get(uid) or await session.scalar(select(MenteeProfile).where(MenteeProfile.user_id == uid))

        if mentor is None and mentee is not None:
            mentor = MentorProfile(
                user_id=uid,
                full_name=mentee.full_name,
                tier_id=rng.choice(tier_ids),
                is_accepting_requests=True,
                expertise_areas=[],
                total_hours_mentored=0,
            )
            session.add(mentor)
            await session.flush()
        if mentee is None and mentor is not None:
            mentee = MenteeProfile(
                user_id=uid,
                full_name=mentor.full_name,
                learning_goals=[],
                education_level="UNDERGRAD",
                is_minor=False,
                guardian_consent_status=GuardianConsentStatus.NOT_REQUIRED,
                cached_credit_score=500,
            )
            session.add(mentee)
            await session.flush()

        if mentor is None or mentee is None:
            # Should not happen, but keep it safe.
            continue

        duals.append(DualRoleUser(user_id=uid, full_name=(mentor.full_name or mentee.full_name or str(uid))))

    return duals[:3]


async def _existing_connection_pairs(session: AsyncSession) -> set[tuple[uuid.UUID, uuid.UUID]]:
    rows = (
        await session.execute(
            select(MentorshipConnection.mentee_id, MentorshipConnection.mentor_id),
        )
    ).all()
    return {(r[0], r[1]) for r in rows}


async def _create_accepted_request_and_connection(
    session: AsyncSession,
    mentee: MenteeProfile,
    mentor: MentorProfile,
) -> tuple[MentorshipRequest, MentorshipConnection]:
    req = MentorshipRequest(
        mentee_id=mentee.id,
        mentor_id=mentor.id,
        status=MentorshipRequestStatus.ACCEPTED,
        intro_message="Looking forward to learning!",
    )
    session.add(req)
    await session.flush()

    conn = MentorshipConnection(
        mentee_id=mentee.id,
        mentor_id=mentor.id,
        status=MentorshipConnectionStatus.ACTIVE,
    )
    session.add(conn)
    await session.flush()

    return req, conn


def _future_slot_times(base: datetime, i: int, j: int) -> tuple[datetime, datetime]:
    start = base + timedelta(days=i + 1, hours=j * 2)
    end = start + timedelta(minutes=30)
    return start, end


async def _ensure_time_slots(
    session: AsyncSession,
    mentor_ids: list[uuid.UUID],
    rng: random.Random,
) -> dict[uuid.UUID, list[TimeSlot]]:
    # mentor_ids are MentorProfile.id (PK)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    slots_by_mentor: dict[uuid.UUID, list[TimeSlot]] = {mid: [] for mid in mentor_ids}

    for idx, mid in enumerate(mentor_ids):
        # Create at least two future slots per mentor (do not delete existing).
        existing = (
            await session.scalars(
                select(TimeSlot)
                .where(and_(TimeSlot.mentor_id == mid, TimeSlot.start_time >= now))
                .order_by(TimeSlot.start_time.asc()),
            )
        ).all()

        future = list(existing)
        need = max(0, 2 - len(future))

        for j in range(need):
            st, et = _future_slot_times(now, idx, j)
            slot = TimeSlot(mentor_id=mid, start_time=st, end_time=et, is_booked=False)
            session.add(slot)
            await session.flush()
            future.append(slot)

        rng.shuffle(future)
        slots_by_mentor[mid] = future

    return slots_by_mentor


async def _create_sessions_goals_and_history(
    session: AsyncSession,
    connections: list[MentorshipConnection],
    mentor_by_id: dict[uuid.UUID, MentorProfile],
    slots_by_mentor_id: dict[uuid.UUID, list[TimeSlot]],
    rng: random.Random,
) -> list[Session]:
    created_sessions: list[Session] = []

    for conn in connections:
        mentor = mentor_by_id[conn.mentor_id]
        slots = slots_by_mentor_id.get(mentor.id, [])
        if not slots:
            continue

        slot = slots.pop()
        status = rng.choice([SessionStatus.SCHEDULED, SessionStatus.COMPLETED])

        sess = Session(connection_id=conn.id, slot_id=slot.id, status=status)
        session.add(sess)
        await session.flush()
        created_sessions.append(sess)

        if status in (SessionStatus.SCHEDULED, SessionStatus.COMPLETED):
            slot.is_booked = True

        # Goals: 2 per connection
        g1 = Goal(connection_id=conn.id, title="Complete skill roadmap", status=GoalStatus.COMPLETED)
        g2 = Goal(connection_id=conn.id, title="Build project", status=GoalStatus.IN_PROGRESS)
        session.add_all([g1, g2])

        # Session history only for COMPLETED
        if status == SessionStatus.COMPLETED:
            hist = SessionHistory(
                session_id=sess.id,
                notes_data={"summary": "Good session", "action_items": ["Practice", "Revise"]},
                mentor_rating=rng.randint(3, 5),
                mentee_rating=rng.randint(3, 5),
            )
            session.add(hist)

    await session.flush()
    return created_sessions


async def _write_user_md(
    *,
    mentors: list[DualRoleUser],
    mentees: list[DualRoleUser],
    auth_accounts: list[tuple[str, str, str]],
    admin_account: tuple[str, str] | None,
    connections: list[tuple[str, str, str]],
) -> str:
    # Repo root (…/mentor-mentee) from …/mentor-mentee-module/backend/scripts/link_seed.py
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "user.md"

    lines: list[str] = ["# Test Users", ""]

    lines += ["## Sign-in Accounts (Non-Admin)", "", "| Full Name | Email | Password |", "|----------|-------|----------|"]
    for full_name, email, password in auth_accounts:
        lines.append(f"| {full_name} | {email} | {password} |")

    lines += ["", "## Admin (keep separate)", ""]
    if admin_account:
        admin_email, admin_password = admin_account
        lines += ["| Email | Password |", "|------|----------|", f"| {admin_email} | {admin_password} |"]
    else:
        lines += ["(Admin credentials not available via this script.)"]

    lines += ["", "## Mentor Profiles", "", "| Full Name | Email | Password |", "|----------|-------|----------|"]
    for u in mentors:
        first, last = _clean_name(u.full_name)
        lines.append(f"| {u.full_name} | {first}@test.com | pass{last} |")

    lines += ["", "## Mentee Profiles", "", "| Full Name | Email | Password |", "|----------|-------|----------|"]
    for u in mentees:
        first, last = _clean_name(u.full_name)
        lines.append(f"| {u.full_name} | {first}@test.com | pass{last} |")

    lines += ["", "## Mentorship Connections", "", "| Mentor | Mentee | Status |", "|-------|-------|--------|"]
    for mentor_name, mentee_name, status in connections:
        lines.append(f"| {mentor_name} | {mentee_name} | {status} |")

    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")
    return str(path)


async def main() -> None:
    rng = _rng()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created_connections: list[MentorshipConnection] = []
    created_sessions: list[Session] = []
    duals: list[DualRoleUser] = []

    async with session_factory() as session:
        async with session.begin():
            mentors, mentees = await _fetch_profiles(session)
            duals = await _ensure_dual_role_users(session, mentors, mentees, rng)

            # Refresh profile lists after any inserts.
            mentors = (await session.scalars(select(MentorProfile).order_by(MentorProfile.id).limit(10))).all()
            mentees = (await session.scalars(select(MenteeProfile).order_by(MenteeProfile.id).limit(10))).all()

            existing_pairs = await _existing_connection_pairs(session)

            # Idempotency: if we already have >= 5 connections, do nothing.
            existing_connection_count = await session.scalar(select(func.count()).select_from(MentorshipConnection))
            target_new = max(0, 5 - int(existing_connection_count or 0))

            rng.shuffle(mentors)
            rng.shuffle(mentees)

            # Create up to `target_new` connections with unique mentors and unique mentees.
            used_mentor_ids: set[uuid.UUID] = set()
            used_mentee_ids: set[uuid.UUID] = set()

            attempts = 0
            while len(created_connections) < target_new and attempts < 500:
                attempts += 1

                mentor = rng.choice([m for m in mentors if m.id not in used_mentor_ids] or mentors)
                mentee = rng.choice([m for m in mentees if m.id not in used_mentee_ids] or mentees)

                if mentor.user_id == mentee.user_id:
                    continue

                pair = (mentee.id, mentor.id)
                if pair in existing_pairs:
                    continue

                _req, conn = await _create_accepted_request_and_connection(session, mentee, mentor)
                existing_pairs.add(pair)
                created_connections.append(conn)
                used_mentor_ids.add(mentor.id)
                used_mentee_ids.add(mentee.id)

            mentor_ids = list({c.mentor_id for c in created_connections})
            mentor_by_id = {m.id: m for m in mentors}

            slots_by_mentor_id = await _ensure_time_slots(session, mentor_ids, rng)
            created_sessions = await _create_sessions_goals_and_history(
                session,
                created_connections,
                mentor_by_id,
                slots_by_mentor_id,
                rng,
            )

    async with session_factory() as session:
        mentor_rows = (
            await session.execute(
                select(MentorProfile.user_id, MentorProfile.full_name).order_by(MentorProfile.full_name.asc()),
            )
        ).all()
        mentee_rows = (
            await session.execute(
                select(MenteeProfile.user_id, MenteeProfile.full_name).order_by(MenteeProfile.full_name.asc()),
            )
        ).all()
        connection_rows = (
            await session.execute(
                select(
                    MentorProfile.full_name,
                    MenteeProfile.full_name,
                    MentorshipConnection.status,
                )
                .select_from(MentorshipConnection)
                .join(MentorProfile, MentorProfile.id == MentorshipConnection.mentor_id)
                .join(MenteeProfile, MenteeProfile.id == MentorshipConnection.mentee_id)
                .order_by(MentorProfile.full_name.asc(), MenteeProfile.full_name.asc()),
            )
        ).all()

    mentor_users = [
        DualRoleUser(user_id=uid, full_name=(name or str(uid)))
        for uid, name in mentor_rows
        if uid is not None
    ]
    mentee_users = [
        DualRoleUser(user_id=uid, full_name=(name or str(uid)))
        for uid, name in mentee_rows
        if uid is not None
    ]

    # Ensure accounts exist in User Service DB so sign-in works.
    combined = list({u.full_name: u for u in (mentor_users + mentee_users)}.values())
    auth_accounts = await _ensure_userservice_accounts(combined)

    # Ensure users_db has profile rows for these accounts (needed for scheduling dropdown).
    await _ensure_userservice_profiles(mentors=mentor_users, mentees=mentee_users, rng=rng)

    # Admin credential is controlled by user-service seed (dev default).
    admin_account: tuple[str, str] | None = ("admin@test.com", "password")

    # Seed + read User Service connections (these drive scheduling dropdown).
    connections = await _seed_userservice_connections_and_slots(rng=rng, target_connections=5)

    user_md_path = await _write_user_md(
        mentors=mentor_users,
        mentees=mentee_users,
        auth_accounts=auth_accounts,
        admin_account=admin_account,
        connections=connections,
    )

    print(f"Created connections: {len(created_connections)}")
    print("Dual-role users:")
    for u in duals:
        print(f"- {u.full_name} ({u.user_id})")
    print(f"Sessions created: {len(created_sessions)}")
    print(f"Wrote: {user_md_path}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

