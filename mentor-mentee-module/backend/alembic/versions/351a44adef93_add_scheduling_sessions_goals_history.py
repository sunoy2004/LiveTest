"""add scheduling sessions goals history

Revision ID: 351a44adef93
Revises: 50dc256a776b
Create Date: 2026-04-16 13:09:57.518129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '351a44adef93'
down_revision: Union[str, None] = '50dc256a776b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "time_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mentor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_booked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["mentor_id"],
            ["mentor_profiles.id"],
            name=op.f("fk_time_slots_mentor_id_mentor_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_time_slots")),
    )
    op.create_index(op.f("ix_time_slots_mentor_id"), "time_slots", ["mentor_id"], unique=False)
    op.create_index(op.f("ix_time_slots_start_time"), "time_slots", ["start_time"], unique=False)
    op.create_index(op.f("ix_time_slots_is_booked"), "time_slots", ["is_booked"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("SCHEDULED", "COMPLETED", name="session_status_enum", native_enum=False),
            nullable=False,
            server_default="SCHEDULED",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["mentorship_connections.id"],
            name=op.f("fk_sessions_connection_id_mentorship_connections"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"],
            ["time_slots.id"],
            name=op.f("fk_sessions_slot_id_time_slots"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
    )
    op.create_index(op.f("ix_sessions_connection_id"), "sessions", ["connection_id"], unique=False)
    op.create_index(op.f("ix_sessions_slot_id"), "sessions", ["slot_id"], unique=False)
    op.create_index(op.f("ix_sessions_status"), "sessions", ["status"], unique=False)

    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("IN_PROGRESS", "COMPLETED", name="goal_status_enum", native_enum=False),
            nullable=False,
            server_default="IN_PROGRESS",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["mentorship_connections.id"],
            name=op.f("fk_goals_connection_id_mentorship_connections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goals")),
    )
    op.create_index(op.f("ix_goals_connection_id"), "goals", ["connection_id"], unique=False)
    op.create_index(op.f("ix_goals_status"), "goals", ["status"], unique=False)

    op.create_table(
        "session_histories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mentor_rating", sa.Integer(), nullable=False),
        sa.Column("mentee_rating", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name=op.f("fk_session_histories_session_id_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_histories")),
        sa.UniqueConstraint("session_id", name=op.f("uq_session_histories_session_id")),
    )
    op.create_index(op.f("ix_session_histories_session_id"), "session_histories", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_session_histories_session_id"), table_name="session_histories")
    op.drop_table("session_histories")

    op.drop_index(op.f("ix_goals_status"), table_name="goals")
    op.drop_index(op.f("ix_goals_connection_id"), table_name="goals")
    op.drop_table("goals")

    op.drop_index(op.f("ix_sessions_status"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_slot_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_connection_id"), table_name="sessions")
    op.drop_table("sessions")

    op.drop_index(op.f("ix_time_slots_is_booked"), table_name="time_slots")
    op.drop_index(op.f("ix_time_slots_start_time"), table_name="time_slots")
    op.drop_index(op.f("ix_time_slots_mentor_id"), table_name="time_slots")
    op.drop_table("time_slots")

    # native_enum=False uses VARCHAR + CHECK; keep explicit drops as no-ops if absent.
