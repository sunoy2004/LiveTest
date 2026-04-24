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


def upgrade() -> None:
    op.create_table(
        "mentor_tiers",
        sa.Column("tier_id", sa.String(length=32), nullable=False),
        sa.Column("tier_name", sa.String(length=128), nullable=False),
        sa.Column("session_credit_cost", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("tier_id", name=op.f("pk_mentor_tiers")),
    )

    op.create_table(
        "mentee_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mentee_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_mentee_profiles_user_id")),
    )
    op.create_index(op.f("ix_mentee_profiles_user_id"), "mentee_profiles", ["user_id"], unique=False)

    op.create_table(
        "mentor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tier_id", sa.String(length=32), nullable=False),
        sa.Column("is_accepting_requests", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "expertise_areas",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("total_hours_mentored", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["tier_id"],
            ["mentor_tiers.tier_id"],
            name=op.f("fk_mentor_profiles_tier_id_mentor_tiers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mentor_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_mentor_profiles_user_id")),
    )
    op.create_index(op.f("ix_mentor_profiles_user_id"), "mentor_profiles", ["user_id"], unique=False)

    op.create_table(
        "mentorship_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mentee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mentor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mentee_id"],
            ["mentee_profiles.id"],
            name=op.f("fk_mentorship_connections_mentee_id_mentee_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mentor_id"],
            ["mentor_profiles.id"],
            name=op.f("fk_mentorship_connections_mentor_id_mentor_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mentorship_connections")),
        sa.UniqueConstraint(
            "mentee_id",
            "mentor_id",
            name="uq_mentorship_connections_mentee_mentor",
        ),
    )
    op.create_index(
        op.f("ix_mentorship_connections_mentee_id"),
        "mentorship_connections",
        ["mentee_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mentorship_connections_mentor_id"),
        "mentorship_connections",
        ["mentor_id"],
        unique=False,
    )

    op.create_table(
        "mentorship_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mentee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mentor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("intro_message", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["mentee_id"],
            ["mentee_profiles.id"],
            name=op.f("fk_mentorship_requests_mentee_id_mentee_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mentor_id"],
            ["mentor_profiles.id"],
            name=op.f("fk_mentorship_requests_mentor_id_mentor_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mentorship_requests")),
    )
    op.create_index(
        op.f("ix_mentorship_requests_mentee_id"),
        "mentorship_requests",
        ["mentee_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mentorship_requests_mentor_id"),
        "mentorship_requests",
        ["mentor_id"],
        unique=False,
    )

    op.create_index(
        "uq_mentorship_requests_pending_mentee_mentor",
        "mentorship_requests",
        ["mentee_id", "mentor_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO mentor_tiers (tier_id, tier_name, session_credit_cost) VALUES
            ('PEER', 'Peer', 50),
            ('PROFESSIONAL', 'Professional', 100),
            ('EXPERT', 'Expert', 250)
            """
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_mentorship_requests_pending_mentee_mentor", table_name="mentorship_requests")
    op.drop_table("mentorship_requests")
    op.drop_table("mentorship_connections")
    op.drop_table("mentor_profiles")
    op.drop_table("mentee_profiles")
    op.drop_table("mentor_tiers")
