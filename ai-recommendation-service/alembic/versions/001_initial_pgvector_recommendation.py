"""Initial match_profiles, match_interactions, pgvector ivfflat index."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "001_initial_pgvector"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
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
    # IVFFlat index (Alembic create_index ivfflat args vary; use raw SQL for portability)
    op.execute(
        """
        CREATE INDEX ix_match_profiles_embedding_ivfflat
        ON match_profiles USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_match_profiles_embedding_ivfflat")
    op.drop_table("match_interactions")
    op.drop_table("match_profiles")
    op.execute("DROP EXTENSION IF EXISTS vector")
