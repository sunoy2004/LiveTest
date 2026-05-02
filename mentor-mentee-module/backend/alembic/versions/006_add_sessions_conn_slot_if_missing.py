"""Add sessions.connection_id and sessions.slot_id when missing (legacy / partial DBs).

Revision ID: 006_sessions_conn_slot
Revises: 005_sessions_align
Create Date: 2026-05-01

Some databases have a `sessions` row without connection_id/slot_id (e.g. table created
from an older branch). The ORM always selects these columns — add them as nullable with FKs.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "006_sessions_conn_slot"
down_revision: Union[str, None] = "005_sessions_align"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("sessions")}
    tables = set(insp.get_table_names())

    if "connection_id" not in cols and "mentorship_connections" in tables:
        op.add_column(
            "sessions",
            sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            op.f("fk_sessions_conn_id"),
            "sessions",
            "mentorship_connections",
            ["connection_id"],
            ["connection_id"],
            ondelete="CASCADE",
        )

    cols = {c["name"] for c in insp.get_columns("sessions")}
    if "slot_id" not in cols and "time_slots" in tables:
        op.add_column(
            "sessions",
            sa.Column("slot_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            op.f("fk_sessions_slot_id"),
            "sessions",
            "time_slots",
            ["slot_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("sessions")}

    if "slot_id" in cols:
        for fk in insp.get_foreign_keys("sessions"):
            if "slot_id" in (fk.get("constrained_columns") or []):
                name = fk.get("name")
                if name:
                    op.drop_constraint(name, "sessions", type_="foreignkey")
                break
        op.drop_column("sessions", "slot_id")

    insp = inspect(conn)
    cols = {c["name"] for c in insp.get_columns("sessions")}
    if "connection_id" in cols:
        for fk in insp.get_foreign_keys("sessions"):
            if "connection_id" in (fk.get("constrained_columns") or []):
                name = fk.get("name")
                if name:
                    op.drop_constraint(name, "sessions", type_="foreignkey")
                break
        op.drop_column("sessions", "connection_id")
