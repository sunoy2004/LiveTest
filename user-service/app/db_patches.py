"""Lightweight DDL for local dev when SQLAlchemy create_all does not alter existing tables."""

from sqlalchemy import inspect, text

from app.db import engine


def apply_schema_patches() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        # --- mentor_tiers (must exist before mentor_profiles FK) ---
        if "mentor_tiers" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE mentor_tiers (
                        tier_id VARCHAR(32) PRIMARY KEY,
                        tier_name VARCHAR(128) NOT NULL,
                        session_credit_cost INTEGER NOT NULL DEFAULT 100
                    )
                    """
                )
            )
        conn.execute(
            text(
                """
                INSERT INTO mentor_tiers (tier_id, tier_name, session_credit_cost) VALUES
                    ('PEER', 'Peer', 10),
                    ('PROFESSIONAL', 'Professional', 30),
                    ('EXPERT', 'Expert', 50)
                ON CONFLICT (tier_id) DO UPDATE SET
                    tier_name = EXCLUDED.tier_name,
                    session_credit_cost = EXCLUDED.session_credit_cost
                """
            )
        )

        # --- admin_profiles (admin role); migrate from legacy users.is_admin then drop column ---
        if "admin_profiles" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE admin_profiles (
                        user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_admin_profiles_user_id ON admin_profiles(user_id)"
                )
            )

        if "users" in tables:
            ucols = {c["name"] for c in inspector.get_columns("users")}
            if "is_mentor" in ucols:
                conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS is_mentor"))
            if "is_mentee" in ucols:
                conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS is_mentee"))
            if "is_admin" not in ucols:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false"
                    )
                )
            conn.execute(
                text(
                    """
                    UPDATE users u
                    SET is_admin = true
                    WHERE EXISTS (SELECT 1 FROM admin_profiles ap WHERE ap.user_id = u.user_id)
                    """
                )
            )

        # --- mentor_profiles: enforce tier FK + NOT NULL (legacy DBs) ---
        if "mentor_profiles" in tables:
            conn.execute(
                text(
                    """
                    UPDATE mentor_profiles
                    SET tier_id = 'PROFESSIONAL'
                    WHERE tier_id IS NULL
                       OR tier_id NOT IN (SELECT tier_id FROM mentor_tiers)
                    """
                )
            )
            conn.execute(
                text("ALTER TABLE mentor_profiles ALTER COLUMN tier_id SET NOT NULL")
            )
            conn.execute(
                text(
                    "ALTER TABLE mentor_profiles DROP CONSTRAINT IF EXISTS mentor_profiles_tier_id_fkey"
                )
            )
            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        ALTER TABLE mentor_profiles
                        ADD CONSTRAINT mentor_profiles_tier_id_fkey
                        FOREIGN KEY (tier_id) REFERENCES mentor_tiers(tier_id) ON DELETE RESTRICT;
                    EXCEPTION
                        WHEN duplicate_object THEN NULL;
                    END $$
                    """
                )
            )

        # --- sessions.slot_id ---
        if "sessions" in tables:
            cols = {c["name"] for c in inspector.get_columns("sessions")}
            if "slot_id" not in cols:
                conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS slot_id UUID"))

        # --- mentorship_requests (legacy DBs only; fresh installs use create_all) ---
        if "mentorship_requests" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE mentorship_requests (
                        request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        mentee_user_id UUID NOT NULL REFERENCES mentee_profiles(user_id) ON DELETE CASCADE,
                        mentor_user_id UUID NOT NULL REFERENCES mentor_profiles(user_id) ON DELETE CASCADE,
                        status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
                        intro_message TEXT NOT NULL DEFAULT ''
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_mentorship_requests_mentee ON mentorship_requests(mentee_user_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_mentorship_requests_mentor ON mentorship_requests(mentor_user_id)"
                )
            )

        # --- reports_and_disputes (after sessions exists) ---
        if "reports_and_disputes" not in tables and "sessions" in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE reports_and_disputes (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
                        kind VARCHAR(64) NOT NULL DEFAULT 'OTHER',
                        session_id UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
                        opened_by_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
                        payload JSON,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        resolved_at TIMESTAMPTZ
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_disputes_session ON reports_and_disputes(session_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_disputes_opener ON reports_and_disputes(opened_by_user_id)"
                )
            )

        # --- TIER_1 / TIER_2 / TIER_3 + mentor pricing + session price (gamification integration) ---
        conn.execute(
            text(
                """
                INSERT INTO mentor_tiers (tier_id, tier_name, session_credit_cost) VALUES
                    ('TIER_1', 'Tier 1', 50),
                    ('TIER_2', 'Tier 2', 100),
                    ('TIER_3', 'Tier 3', 150)
                ON CONFLICT (tier_id) DO UPDATE SET
                    tier_name = EXCLUDED.tier_name,
                    session_credit_cost = EXCLUDED.session_credit_cost
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE mentor_profiles ADD COLUMN IF NOT EXISTS pricing_tier VARCHAR(16) NOT NULL DEFAULT 'TIER_2'
                """
            )
        )
        conn.execute(
            text("ALTER TABLE mentor_profiles ADD COLUMN IF NOT EXISTS base_credit_override INTEGER")
        )
        # --- mentor_profiles rich fields (view profile + AI similarity) ---
        conn.execute(text("ALTER TABLE mentor_profiles ADD COLUMN IF NOT EXISTS headline VARCHAR(256)"))
        conn.execute(text("ALTER TABLE mentor_profiles ADD COLUMN IF NOT EXISTS bio TEXT"))
        conn.execute(text("ALTER TABLE mentor_profiles ADD COLUMN IF NOT EXISTS current_title VARCHAR(128)"))
        conn.execute(text("ALTER TABLE mentor_profiles ADD COLUMN IF NOT EXISTS current_company VARCHAR(128)"))
        conn.execute(text("ALTER TABLE mentor_profiles ADD COLUMN IF NOT EXISTS years_experience INTEGER"))
        conn.execute(text("ALTER TABLE mentor_profiles ADD COLUMN IF NOT EXISTS professional_experiences JSON"))
        conn.execute(
            text(
                """
                UPDATE mentor_profiles SET pricing_tier = CASE tier_id
                    WHEN 'PEER' THEN 'TIER_1'
                    WHEN 'PROFESSIONAL' THEN 'TIER_2'
                    WHEN 'EXPERT' THEN 'TIER_3'
                    ELSE 'TIER_2'
                END
                """
            )
        )
        conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS price_charged INTEGER"))
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    ALTER TABLE sessions ADD COLUMN mentor_user_id UUID REFERENCES mentor_profiles(user_id) ON DELETE SET NULL;
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$
                """
            )
        )
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    ALTER TABLE sessions ADD COLUMN mentee_user_id UUID REFERENCES mentee_profiles(user_id) ON DELETE SET NULL;
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE sessions s
                SET mentor_user_id = c.mentor_user_id,
                    mentee_user_id = c.mentee_user_id
                FROM mentorship_connections c
                WHERE s.connection_id = c.connection_id
                  AND (s.mentor_user_id IS NULL OR s.mentee_user_id IS NULL)
                """
            )
        )

        # --- session_booking_requests + time_slots.pending_request_id ---
        if "session_booking_requests" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE session_booking_requests (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        connection_id UUID NOT NULL REFERENCES mentorship_connections(connection_id) ON DELETE CASCADE,
                        slot_id UUID NOT NULL REFERENCES time_slots(id) ON DELETE CASCADE,
                        status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
                        agreed_cost INTEGER NOT NULL,
                        session_id UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        resolved_at TIMESTAMPTZ
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_sbr_connection ON session_booking_requests(connection_id)"
                )
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_sbr_slot ON session_booking_requests(slot_id)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_sbr_status ON session_booking_requests(status)")
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_sbr_session ON session_booking_requests(session_id)"
                )
            )
        if "time_slots" in tables:
            tcols = {c["name"] for c in inspector.get_columns("time_slots")}
            if "pending_request_id" not in tcols:
                conn.execute(
                    text(
                        "ALTER TABLE time_slots ADD COLUMN IF NOT EXISTS pending_request_id UUID"
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_ts_pending_req ON time_slots(pending_request_id)"
                    )
                )
