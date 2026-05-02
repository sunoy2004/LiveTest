"""Shrink match_profiles.embedding to vector(768) to match sentence-transformers default.

Production drift may have created vector(1536). pgvector cannot cast between dimensions;
we truncate match_profiles (rebuild via POST /internal/matchmaking/reindex) and alter type.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "002_embedding_768"
down_revision = "001_initial_pgvector"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 768
INDEX_NAME = "ix_match_profiles_embedding_ivfflat"


def _embedding_column_format() -> str | None:
    bind = op.get_bind()
    row = bind.execute(
        text(
            """
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname = 'match_profiles'
              AND a.attname = 'embedding'
              AND a.attnum > 0
              AND NOT a.attisdropped
            """
        )
    ).fetchone()
    if row is None:
        return None
    return str(row[0]).strip()


def upgrade() -> None:
    fmt = _embedding_column_format()
    if fmt is None:
        return

    target = f"vector({EMBEDDING_DIM})"
    op.execute(text(f"DROP INDEX IF EXISTS {INDEX_NAME}"))
    if fmt != target:
        op.execute(text("TRUNCATE TABLE match_profiles"))
        op.execute(
            text(
                f"ALTER TABLE match_profiles "
                f"ALTER COLUMN embedding TYPE vector({EMBEDDING_DIM})"
            )
        )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS {INDEX_NAME}
            ON match_profiles USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10);
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {INDEX_NAME}"))
    op.execute(text("TRUNCATE TABLE match_profiles"))
    op.execute(
        text(
            "ALTER TABLE match_profiles "
            "ALTER COLUMN embedding TYPE vector(1536)"
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS {INDEX_NAME}
            ON match_profiles USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10);
            """
        )
    )
