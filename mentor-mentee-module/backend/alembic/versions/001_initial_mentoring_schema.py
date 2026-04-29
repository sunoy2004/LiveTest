"""initial mentoring schema

Revision ID: 001_initial
Revises:
Create Date: 2026-04-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy import inspect

def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    existing_tables = insp.get_table_names()
    
    # Helper to check if a column exists
    def column_exists(table, column):
        cols = insp.get_columns(table)
        return any(c["name"] == column for c in cols)

    # 1. Users Table (Replica)
    if "users" in existing_tables:
        if not column_exists("users", "user_id"):
            op.drop_table("users")
            existing_tables.remove("users")
    
    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.Text(), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("user_id", name=op.f("pk_users")),
            sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        )

    # 2. Mentor Tiers
    if "mentor_tiers" in existing_tables:
        if not column_exists("mentor_tiers", "tier_id"):
            op.execute(sa.text("DROP TABLE mentor_tiers CASCADE"))
            existing_tables.remove("mentor_tiers")

    if "mentor_tiers" not in existing_tables:
        op.create_table(
            "mentor_tiers",
            sa.Column("tier_id", sa.String(length=32), nullable=False),
            sa.Column("tier_name", sa.String(length=128), nullable=False),
            sa.Column("session_credit_cost", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("tier_id", name=op.f("pk_mentor_tiers")),
        )

    # 3. Mentee Profiles (PK is user_id)
    if "mentee_profiles" in existing_tables:
        if not column_exists("mentee_profiles", "user_id"):
            op.execute(sa.text("DROP TABLE mentee_profiles CASCADE"))
            existing_tables.remove("mentee_profiles")

    if "mentee_profiles" not in existing_tables:
        op.create_table(
            "mentee_profiles",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column(
                "learning_goals",
                postgresql.ARRAY(sa.Text()),
                server_default=sa.text("'{}'::text[]"),
                nullable=False,
            ),
            sa.Column("education_level", sa.String(length=64), nullable=False),
            sa.Column("is_minor", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("guardian_consent_status", sa.String(length=32), nullable=False),
            sa.Column("cached_credit_score", sa.Integer(), server_default="0", nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_mentee_profiles_user_id"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", name=op.f("pk_mentee_profiles")),
        )
        op.create_index(op.f("ix_mentee_profiles_user_id"), "mentee_profiles", ["user_id"], unique=False)
        # GIN index for learning_goals array
        op.execute(sa.text("CREATE INDEX ix_mentee_profiles_learning_goals_gin ON mentee_profiles USING gin (learning_goals)"))

    # 4. Mentor Profiles (PK is user_id)
    if "mentor_profiles" in existing_tables:
        if not column_exists("mentor_profiles", "user_id"):
            op.execute(sa.text("DROP TABLE mentor_profiles CASCADE"))
            existing_tables.remove("mentor_profiles")

    if "mentor_profiles" not in existing_tables:
        op.create_table(
            "mentor_profiles",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column("tier_id", sa.String(length=32), nullable=False),
            sa.Column("is_accepting_requests", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column(
                "expertise_areas",
                postgresql.ARRAY(sa.Text()),
                server_default=sa.text("'{}'::text[]"),
                nullable=False,
            ),
            sa.Column("total_hours_mentored", sa.Integer(), server_default="0", nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_mentor_profiles_user_id"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["tier_id"],
                ["mentor_tiers.tier_id"],
                name=op.f("fk_mentor_profiles_tier_id_mentor_tiers"),
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("user_id", name=op.f("pk_mentor_profiles")),
        )
        op.create_index(op.f("ix_mentor_profiles_user_id"), "mentor_profiles", ["user_id"], unique=False)
        # GIN index for expertise_areas array
        op.execute(sa.text("CREATE INDEX ix_mentor_profiles_expertise_areas_gin ON mentor_profiles USING gin (expertise_areas)"))

    # 5. Connections (PK is connection_id)
    if "mentorship_connections" not in existing_tables:
        op.create_table(
            "mentorship_connections",
            sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mentee_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mentor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
            sa.ForeignKeyConstraint(["mentee_user_id"], ["mentee_profiles.user_id"], name=op.f("fk_connections_mentee_id"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["mentor_user_id"], ["mentor_profiles.user_id"], name=op.f("fk_connections_mentor_id"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("connection_id", name=op.f("pk_mentorship_connections")),
            sa.UniqueConstraint("mentee_user_id", "mentor_user_id", name="uq_mentorship_connections_mentee_mentor"),
        )

    # 6. Requests (PK is request_id)
    if "mentorship_requests" not in existing_tables:
        op.create_table(
            "mentorship_requests",
            sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mentee_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mentor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
            sa.Column("intro_message", sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(["mentee_user_id"], ["mentee_profiles.user_id"], name=op.f("fk_requests_mentee_id"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["mentor_user_id"], ["mentor_profiles.user_id"], name=op.f("fk_requests_mentor_id"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("request_id", name=op.f("pk_mentorship_requests")),
        )
        op.create_index("uq_mentorship_requests_pending", "mentorship_requests", ["mentee_user_id", "mentor_user_id"], unique=True, postgresql_where=sa.text("status = 'PENDING'"))

    # 7. Time Slots
    if "time_slots" not in existing_tables:
        op.create_table(
            "time_slots",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mentor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_booked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.ForeignKeyConstraint(["mentor_user_id"], ["mentor_profiles.user_id"], name=op.f("fk_time_slots_mentor_id"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_time_slots")),
        )

    # 8. Sessions (PK is session_id)
    if "sessions" not in existing_tables:
        op.create_table(
            "sessions",
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("slot_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="SCHEDULED", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["mentorship_connections.connection_id"], name=op.f("fk_sessions_conn_id"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["slot_id"], ["time_slots.id"], name=op.f("fk_sessions_slot_id"), ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("session_id", name=op.f("pk_sessions")),
        )

    # 9. Goals
    if "goals" not in existing_tables:
        op.create_table(
            "goals",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=512), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["connection_id"], ["mentorship_connections.connection_id"], name=op.f("fk_goals_conn_id"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_goals")),
        )

    # 10. Session Histories (Plural name to match model)
    if "session_histories" not in existing_tables:
        if "session_history" in existing_tables:
            op.drop_table("session_history")
            
        op.create_table(
            "session_histories",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("notes_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("mentor_rating", sa.Integer(), nullable=False),
            sa.Column("mentee_rating", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"], name=op.f("fk_histories_session_id"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_session_histories")),
            sa.UniqueConstraint("session_id", name=op.f("uq_session_histories_session_id")),
        )

    # 11. Booking Requests
    if "session_booking_requests" not in existing_tables:
        op.create_table(
            "session_booking_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("slot_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
            sa.Column("agreed_cost", sa.Integer(), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["connection_id"], ["mentorship_connections.connection_id"], name=op.f("fk_booking_conn_id"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["slot_id"], ["time_slots.id"], name=op.f("fk_booking_slot_id"), ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"], name=op.f("fk_booking_sess_id"), ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_requests")),
        )

    # 12. Reports
    if "reports_and_disputes" not in existing_tables:
        op.create_table(
            "reports_and_disputes",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="OPEN", nullable=False),
            sa.Column("kind", sa.String(length=64), server_default="OTHER", nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("opened_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"], name=op.f("fk_reports_sess_id"), ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["opened_by_user_id"], ["users.user_id"], name=op.f("fk_reports_user_id"), ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_reports_and_disputes")),
        )

    # Initial data seeding
    op.execute(sa.text("INSERT INTO mentor_tiers (tier_id, tier_name, session_credit_cost) SELECT 'PEER', 'Peer', 50 WHERE NOT EXISTS (SELECT 1 FROM mentor_tiers WHERE tier_id = 'PEER')"))
    op.execute(sa.text("INSERT INTO mentor_tiers (tier_id, tier_name, session_credit_cost) SELECT 'PROFESSIONAL', 'Professional', 100 WHERE NOT EXISTS (SELECT 1 FROM mentor_tiers WHERE tier_id = 'PROFESSIONAL')"))
    op.execute(sa.text("INSERT INTO mentor_tiers (tier_id, tier_name, session_credit_cost) SELECT 'EXPERT', 'Expert', 250 WHERE NOT EXISTS (SELECT 1 FROM mentor_tiers WHERE tier_id = 'EXPERT')"))

def downgrade() -> None:
    op.drop_table("reports_and_disputes")
    op.drop_table("session_booking_requests")
    op.drop_table("session_histories")
    op.drop_table("goals")
    op.drop_table("sessions")
    op.drop_table("time_slots")
    op.drop_table("mentorship_requests")
    op.drop_table("mentorship_connections")
    op.drop_table("mentor_profiles")
    op.drop_table("mentee_profiles")
    op.drop_table("mentor_tiers")
    op.drop_table("users")
