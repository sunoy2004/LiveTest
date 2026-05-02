"""Drop mentee_profiles.cached_credit_score — credits are authoritative in gamification only.

Revision ID: 002_cached_credit
Revises: 001_initial
Create Date: 2026-05-01

Removes legacy column if present (ORM no longer maps it).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "002_cached_credit"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "mentee_profiles" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("mentee_profiles")}
    if "cached_credit_score" not in cols:
        return
    op.drop_column("mentee_profiles", "cached_credit_score")


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "mentee_profiles" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("mentee_profiles")}
    if "cached_credit_score" in cols:
        return
    op.add_column(
        "mentee_profiles",
        sa.Column(
            "cached_credit_score",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
