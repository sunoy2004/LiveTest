"""seed RESOLVE_NO_SHOW_REFUND rule

Revision ID: 005_no_show_refund
Revises: 004_wallet_lifetime_idx
Create Date: 2026-04-18

"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_no_show_refund"
down_revision: Union[str, None] = "004_wallet_lifetime_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.execute(
        sa.text(
            """
            INSERT INTO activity_rules (
                rule_code, transaction_type, base_credit_value, is_active, cooldown_seconds, updated_at
            )
            VALUES (
                'RESOLVE_NO_SHOW_REFUND', 'EARN', 1, TRUE, 0, :ts
            )
            ON CONFLICT (rule_code) DO NOTHING
            """
        ).bindparams(ts=now)
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM activity_rules WHERE rule_code = 'RESOLVE_NO_SHOW_REFUND'"
    )
