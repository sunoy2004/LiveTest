"""wallet constraints + ledger created_at index

Revision ID: 003_wallet_ck
Revises: 002_constraints
Create Date: 2026-04-17

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "003_wallet_ck"
down_revision: Union[str, None] = "002_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_wallet_current_balance_nonneg",
        "wallets",
        "current_balance >= 0",
    )
    # Fast history scans by time (admin ledger viewer, audits).
    op.create_index(
        "ix_ledger_transactions_created_at",
        "ledger_transactions",
        ["created_at"],
    )
    # Ensure BOOK_MENTOR_SESSION exists for booking flow via internal deduct API.
    op.execute(
        """
        INSERT INTO activity_rules (rule_code, transaction_type, base_credit_value, is_active, cooldown_seconds, updated_at)
        VALUES ('BOOK_MENTOR_SESSION', 'SPEND', 10, TRUE, 0, NOW())
        ON CONFLICT (rule_code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_ledger_transactions_created_at", table_name="ledger_transactions")
    op.drop_constraint("ck_wallet_current_balance_nonneg", "wallets", type_="check")

