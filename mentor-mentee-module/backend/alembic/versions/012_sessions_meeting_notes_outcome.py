"""Add shared meeting_notes and meeting_outcome on sessions (mentor + mentee editable).

Revision ID: 012_session_meeting_fields
Revises: 011_users_drop_email
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "012_session_meeting_fields"
down_revision: Union[str, None] = "011_users_drop_email"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("sessions")}
    if "meeting_notes" not in cols:
        op.add_column("sessions", sa.Column("meeting_notes", sa.Text(), nullable=True))
    if "meeting_outcome" not in cols:
        op.add_column("sessions", sa.Column("meeting_outcome", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("sessions")}
    if "meeting_notes" in cols:
        op.drop_column("sessions", "meeting_notes")
    if "meeting_outcome" in cols:
        op.drop_column("sessions", "meeting_outcome")
