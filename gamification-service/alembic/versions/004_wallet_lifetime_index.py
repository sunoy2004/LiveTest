"""index wallets lifetime_earned desc

Revision ID: 004_wallet_lifetime_idx
Revises: 003_wallet_ck
Create Date: 2026-04-17

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "004_wallet_lifetime_idx"
down_revision: Union[str, None] = "003_wallet_ck"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres supports DESC indexes; IF NOT EXISTS makes this safe on re-runs.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_wallet_lifetime ON wallets (lifetime_earned DESC, user_id ASC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_wallet_lifetime")

