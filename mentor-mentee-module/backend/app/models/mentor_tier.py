"""Global mentor pricing tiers (`tier_id` PK) — mentors reference via `mentor_profiles.tier_id`."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MentorTier(Base):
    __tablename__ = "mentor_tiers"

    tier_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tier_name: Mapped[str] = mapped_column(String(128), nullable=False)
    session_credit_cost: Mapped[int] = mapped_column(Integer, nullable=False)

    mentor_profiles: Mapped[list["MentorProfile"]] = relationship(
        "MentorProfile",
        back_populates="tier_row",
    )
