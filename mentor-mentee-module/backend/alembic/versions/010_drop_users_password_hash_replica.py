"""Remove credential columns from mentoring `users` replica (canonical auth is User Service).

Revision ID: 010_users_replica_trim
Revises: 009_sessions_credit_cost

`password_hash` must not be stored outside User Service. `is_admin` on users was legacy
001-only; admin is determined from JWT in this service.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "010_users_replica_trim"
down_revision: Union[str, None] = "009_sessions_credit_cost"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "password_hash" in cols:
        op.drop_column("users", "password_hash")
    if "is_admin" in cols:
        op.drop_column("users", "is_admin")


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "password_hash" not in cols:
        op.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT NOT NULL DEFAULT ''"))
    if "is_admin" not in cols:
        op.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false"
            )
        )
