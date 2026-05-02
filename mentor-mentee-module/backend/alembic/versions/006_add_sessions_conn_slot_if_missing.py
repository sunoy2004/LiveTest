"""Add sessions.connection_id and sessions.slot_id when missing (legacy / partial DBs).

Revision ID: 006_sessions_conn_slot
Revises: 005_sessions_align
Create Date: 2026-05-01

Some databases have a `sessions` table without connection_id/slot_id. The ORM selects these
columns — add them as nullable UUIDs.

FK to mentorship_connections(connection_id) is only added when that column exists (older
001 migrations used connection_id as PK; some live DBs use a composite PK on connections
without connection_id — FK would be invalid).
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

revision: str = "006_sessions_conn_slot"
down_revision: Union[str, None] = "005_sessions_align"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return

    tables = set(insp.get_table_names())
    s_cols = {c["name"] for c in insp.get_columns("sessions")}

    # Use raw DDL so column exists before any CONSTRAINT; PG11+ IF NOT EXISTS is idempotent.
    if "connection_id" not in s_cols:
        op.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS connection_id UUID"))

    if "mentorship_connections" in tables:
        mc_cols = {c["name"] for c in insp.get_columns("mentorship_connections")}
        if "connection_id" in mc_cols:
            op.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname = 'fk_sessions_conn_id'
                        ) THEN
                            ALTER TABLE sessions
                            ADD CONSTRAINT fk_sessions_conn_id
                            FOREIGN KEY (connection_id)
                            REFERENCES mentorship_connections (connection_id)
                            ON DELETE CASCADE;
                        END IF;
                    END $$;
                    """
                )
            )

    insp = inspect(conn)
    s_cols = {c["name"] for c in insp.get_columns("sessions")}

    if "slot_id" not in s_cols and "time_slots" in tables:
        op.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS slot_id UUID"))
        ts_cols = {c["name"] for c in insp.get_columns("time_slots")}
        if "id" in ts_cols:
            op.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname = 'fk_sessions_slot_id'
                        ) THEN
                            ALTER TABLE sessions
                            ADD CONSTRAINT fk_sessions_slot_id
                            FOREIGN KEY (slot_id)
                            REFERENCES time_slots (id)
                            ON DELETE RESTRICT;
                        END IF;
                    END $$;
                    """
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if "sessions" not in insp.get_table_names():
        return

    op.execute(
        text(
            """
            ALTER TABLE sessions DROP CONSTRAINT IF EXISTS fk_sessions_slot_id;
            """
        )
    )
    op.execute(
        text(
            """
            ALTER TABLE sessions DROP CONSTRAINT IF EXISTS fk_sessions_conn_id;
            """
        )
    )

    cols = {c["name"] for c in insp.get_columns("sessions")}
    if "slot_id" in cols:
        op.execute(text("ALTER TABLE sessions DROP COLUMN IF EXISTS slot_id"))

    cols = {c["name"] for c in inspect(conn).get_columns("sessions")}
    if "connection_id" in cols:
        op.execute(text("ALTER TABLE sessions DROP COLUMN IF EXISTS connection_id"))
