"""Drop `users.email` from mentoring replica (identity lives in User Service + JWT).

Revision ID: 011_users_drop_email
Revises: 010_users_replica_trim
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "011_users_drop_email"
down_revision: Union[str, None] = "010_users_replica_trim"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "email" not in cols:
        return
    op.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_email"))
    op.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key"))
    op.drop_column("users", "email")


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "email" in cols:
        return
    op.add_column(
        "users",
        sa.Column("email", sa.Text(), nullable=False, server_default="unknown@local.invalid"),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.alter_column("users", "email", server_default=None)
