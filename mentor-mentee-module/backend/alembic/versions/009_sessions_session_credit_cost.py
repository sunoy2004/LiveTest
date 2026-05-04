"""Store credits charged at booking on sessions for admin / reporting.

Revision ID: 009_sessions_credit_cost
Revises: 008_requests_intro_default

`accept_booking_request` deducts via gamification (BOOK_MENTOR_SESSION rule + tier fallback).
Admin list previously joined mentor_tiers only, showing PEER default (e.g. 50) instead of
the amount actually charged. New column holds the value persisted at accept time.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "009_sessions_credit_cost"
down_revision: Union[str, None] = "008_requests_intro_default"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("sessions")}
    if "session_credit_cost" not in cols:
        op.add_column(
            "sessions",
            sa.Column("session_credit_cost", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("sessions")}
    if "session_credit_cost" in cols:
        op.drop_column("sessions", "session_credit_cost")
