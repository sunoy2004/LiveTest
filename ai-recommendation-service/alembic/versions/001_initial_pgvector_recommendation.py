"""Initial match_profiles, match_interactions, pgvector ivfflat index.

Idempotent: tables may already exist on the shared `mentoring` database from a prior
deploy or manual DDL while `alembic_version_ai_recommendation` was empty or reset.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision = "001_initial_pgvector"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn = op.get_bind()
    insp = inspect(conn)
    tables = set(insp.get_table_names())

    if "match_profiles" not in tables:
        op.create_table(
            "match_profiles",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("role", sa.String(16), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("combined_text_payload", sa.Text(), nullable=False, server_default=""),
            sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.CheckConstraint(
                "role IN ('MENTOR', 'MENTEE', 'BOTH')",
                name="ck_match_profiles_role",
            ),
        )

    if "match_interactions" not in tables:
        op.create_table(
            "match_interactions",
            sa.Column("interaction_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("source_user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("interaction_type", sa.String(32), nullable=False),
            sa.Column("weight", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.CheckConstraint(
                "interaction_type IN ('REJECTED_SUGGESTION', 'SUCCESSFUL_MENTORSHIP')",
                name="ck_match_interactions_type",
            ),
            sa.UniqueConstraint(
                "source_user_id",
                "target_user_id",
                "interaction_type",
                name="uq_match_interactions_source_target_type",
            ),
        )

    # Safe when table pre-existed without index (shared DB drift).
    op.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_match_profiles_embedding_ivfflat
            ON match_profiles USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10);
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS ix_match_profiles_embedding_ivfflat"))
    conn = op.get_bind()
    insp = inspect(conn)
    tables = set(insp.get_table_names())
    if "match_interactions" in tables:
        op.drop_table("match_interactions")
    if "match_profiles" in tables:
        op.drop_table("match_profiles")
    op.execute(text("DROP EXTENSION IF EXISTS vector"))
