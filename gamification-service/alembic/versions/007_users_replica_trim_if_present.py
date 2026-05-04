"""If a `users` replica exists in gamification DB, drop credential / email columns.

Revision ID: 007_users_replica_trim
Revises: 006_mentor_no_show

Canonical identity stays in User Service. Core gamification migrations do not create
`users`; some deployments add it — this revision is idempotent.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "007_users_replica_trim"
down_revision: Union[str, None] = "006_mentor_no_show"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "users" not in insp.get_table_names():
        return
    drops = (
        "email",
        "password_hash",
        "full_name",
        "first_name",
        "last_name",
        "is_admin",
    )
    for col in drops:
        op.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {col}"))


def downgrade() -> None:
    pass
