"""Set intro_message default and backfill empty strings.

Revision ID: 008_requests_intro_default
Revises: 007_requests_intro
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "008_requests_intro_default"
down_revision: Union[str, None] = "007_requests_intro"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MSG = "I'd like to request a mentorship connection with you."


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "mentorship_requests" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("mentorship_requests")}
    if "intro_message" not in cols:
        return
    # Backfill rows with no custom message stored as empty
    op.execute(
        text(
            """
            UPDATE mentorship_requests
            SET intro_message = :msg
            WHERE coalesce(trim(intro_message), '') = ''
            """
        ).bindparams(msg=_MSG)
    )
    op.execute(
        text(
            """
            ALTER TABLE mentorship_requests
            ALTER COLUMN intro_message SET DEFAULT 'I''d like to request a mentorship connection with you.'
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "mentorship_requests" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("mentorship_requests")}
    if "intro_message" not in cols:
        return
    op.execute(
        text(
            """
            ALTER TABLE mentorship_requests
            ALTER COLUMN intro_message SET DEFAULT ''
            """
        )
    )
