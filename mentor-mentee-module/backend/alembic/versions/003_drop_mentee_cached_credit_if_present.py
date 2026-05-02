"""Ensure mentee_profiles.cached_credit_score is removed (idempotent).

Revision ID: 003_drop_cache_col
Revises: 002_cached_credit
Create Date: 2026-05-01

Databases that were already stamped at 002_cached_credit from an older "add column"
revision never re-ran 002 after we changed it. This migration runs for everyone at 002+.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "003_drop_cache_col"
down_revision: Union[str, None] = "002_cached_credit"
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
