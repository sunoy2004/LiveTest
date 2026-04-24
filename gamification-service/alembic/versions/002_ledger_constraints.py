"""add ledger integrity constraints

Revision ID: 002_constraints
Revises: 001_initial
Create Date: 2026-04-17

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_constraints"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ledger truth must never store no-op transactions.
    op.create_check_constraint(
        "ck_ledger_amount_nonzero",
        "ledger_transactions",
        "amount <> 0",
    )
    # Ledger should never represent negative balance-after.
    op.create_check_constraint(
        "ck_ledger_balance_after_nonneg",
        "ledger_transactions",
        "balance_after >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ledger_balance_after_nonneg", "ledger_transactions", type_="check")
    op.drop_constraint("ck_ledger_amount_nonzero", "ledger_transactions", type_="check")

