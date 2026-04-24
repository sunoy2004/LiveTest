"""initial gamification tables and seed rules

Revision ID: 001_initial
Revises:
Create Date: 2026-04-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_rules",
        sa.Column("rule_code", sa.String(length=128), nullable=False),
        sa.Column("transaction_type", sa.String(length=16), nullable=False),
        sa.Column("base_credit_value", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("rule_code"),
    )
    op.create_table(
        "wallets",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_balance", sa.Integer(), nullable=False),
        sa.Column("lifetime_earned", sa.Integer(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "ledger_transactions",
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_code", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("transaction_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_ledger_idempotency"),
    )
    op.create_index(
        "ix_ledger_transactions_user_id",
        "ledger_transactions",
        ["user_id"],
    )
    op.create_index(
        "ix_ledger_transactions_rule_code",
        "ledger_transactions",
        ["rule_code"],
    )
    op.create_index(
        "ix_ledger_user_rule_created",
        "ledger_transactions",
        ["user_id", "rule_code", "created_at"],
    )

    rules = sa.table(
        "activity_rules",
        sa.column("rule_code", sa.String),
        sa.column("transaction_type", sa.String),
        sa.column("base_credit_value", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("cooldown_seconds", sa.Integer),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    op.bulk_insert(
        rules,
        [
            {
                "rule_code": "DELIVER_MENTOR_SESSION",
                "transaction_type": "EARN",
                "base_credit_value": 5,
                "is_active": True,
                "cooldown_seconds": 0,
                "updated_at": now,
            },
            {
                "rule_code": "ATTEND_MENTEE_SESSION",
                "transaction_type": "EARN",
                "base_credit_value": 10,
                "is_active": True,
                "cooldown_seconds": 0,
                "updated_at": now,
            },
            {
                "rule_code": "BOOKING_SPEND",
                "transaction_type": "SPEND",
                "base_credit_value": 10,
                "is_active": True,
                "cooldown_seconds": 0,
                "updated_at": now,
            },
            {
                "rule_code": "BOOK_MENTOR_SESSION",
                "transaction_type": "SPEND",
                "base_credit_value": 10,
                "is_active": True,
                "cooldown_seconds": 0,
                "updated_at": now,
            },
            {
                "rule_code": "LEGACY_CREDIT_ADD",
                "transaction_type": "EARN",
                "base_credit_value": 1,
                "is_active": True,
                "cooldown_seconds": 0,
                "updated_at": now,
            },
            {
                "rule_code": "ADMIN_GRANT",
                "transaction_type": "EARN",
                "base_credit_value": 1,
                "is_active": True,
                "cooldown_seconds": 0,
                "updated_at": now,
            },
            {
                "rule_code": "ADMIN_DEDUCT",
                "transaction_type": "SPEND",
                "base_credit_value": 1,
                "is_active": True,
                "cooldown_seconds": 0,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_ledger_user_rule_created", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_rule_code", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_user_id", table_name="ledger_transactions")
    op.drop_table("ledger_transactions")
    op.drop_table("wallets")
    op.drop_table("activity_rules")
