"""add full_name and search indexes

Revision ID: 50dc256a776b
Revises: 001_initial
Create Date: 2026-04-16 12:05:58.347173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50dc256a776b'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mentor_profiles", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.add_column("mentee_profiles", sa.Column("full_name", sa.String(length=255), nullable=True))

    op.create_index("ix_mentor_profiles_full_name", "mentor_profiles", ["full_name"], unique=False)
    op.create_index("ix_mentee_profiles_full_name", "mentee_profiles", ["full_name"], unique=False)

    op.create_index(
        "ix_mentor_profiles_expertise_areas_gin",
        "mentor_profiles",
        ["expertise_areas"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_mentor_profiles_expertise_areas_gin", table_name="mentor_profiles")
    op.drop_index("ix_mentee_profiles_full_name", table_name="mentee_profiles")
    op.drop_index("ix_mentor_profiles_full_name", table_name="mentor_profiles")

    op.drop_column("mentee_profiles", "full_name")
    op.drop_column("mentor_profiles", "full_name")
