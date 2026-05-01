"""Global mentor pricing tiers (`tier_id` PK). Per-mentor tier may live on `mentor_profiles.tier_id` when migrated."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MentorTier(Base):
    __tablename__ = "mentor_tiers"

    tier_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tier_name: Mapped[str] = mapped_column(String(128), nullable=False)
    session_credit_cost: Mapped[int] = mapped_column(Integer, nullable=False)
