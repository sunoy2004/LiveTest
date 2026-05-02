"""Add mentee_profiles.cached_credit_score if missing (synced from gamification).

Revision ID: 004_cached_credit_col
Revises: 003_drop_cache_col
Create Date: 2026-05-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "004_cached_credit_col"
down_revision: Union[str, None] = "003_drop_cache_col"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "mentee_profiles" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("mentee_profiles")}
    if "cached_credit_score" not in cols:
        return
    op.drop_column("mentee_profiles", "cached_credit_score")
