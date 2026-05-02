"""Add intro_message to mentorship_requests when missing (composite-PK schema).

Revision ID: 007_requests_intro
Revises: 006_sessions_conn_slot
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "007_requests_intro"
down_revision: Union[str, None] = "006_sessions_conn_slot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "mentorship_requests" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("mentorship_requests")}
    if "intro_message" in cols:
        return
    op.add_column(
        "mentorship_requests",
        sa.Column(
            "intro_message",
            sa.Text(),
            nullable=False,
            server_default=sa.text(
                "'I''d like to request a mentorship connection with you.'"
            ),
        ),
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "mentorship_requests" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("mentorship_requests")}
    if "intro_message" not in cols:
        return
    op.drop_column("mentorship_requests", "intro_message")
