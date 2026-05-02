"""Align sessions with ORM: mentor/mentee/times + nullable connection_id/slot_id.

Revision ID: 005_sessions_align
Revises: 004_cached_credit_col
Create Date: 2026-05-01

Older schema (001) required connection_id + slot_id NOT NULL while accept_booking_request
only set mentor/mentee/start/end — causing INSERT failures when mentors accept requests.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "005_sessions_align"
down_revision: Union[str, None] = "004_cached_credit_col"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return

    cols = {c["name"]: c for c in insp.get_columns("sessions")}

    if "mentor_user_id" not in cols:
        op.add_column(
            "sessions",
            sa.Column(
                "mentor_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                nullable=True,
            ),
        )
    if "mentee_user_id" not in cols:
        op.add_column(
            "sessions",
            sa.Column(
                "mentee_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                nullable=True,
            ),
        )
    if "start_time" not in cols:
        op.add_column(
            "sessions",
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        )
    if "end_time" not in cols:
        op.add_column(
            "sessions",
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        )

    # Allow inserts that only set mentor/mentee/slot times (connection optional).
    if "connection_id" in cols and cols["connection_id"].get("nullable") is False:
        op.alter_column("sessions", "connection_id", nullable=True)
    if "slot_id" in cols and cols["slot_id"].get("nullable") is False:
        op.alter_column("sessions", "slot_id", nullable=True)


def downgrade() -> None:
    """Non-destructive: only tighten nullability if columns exist (may fail if nulls present)."""
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("sessions")}
    if "connection_id" in cols:
        try:
            op.alter_column("sessions", "connection_id", nullable=False)
        except Exception:
            pass
    if "slot_id" in cols:
        try:
            op.alter_column("sessions", "slot_id", nullable=False)
        except Exception:
            pass
