from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, User
from app.services.mentor_pricing import resolve_mentor_session_price


def _display_name(email: str) -> str:
    local = email.split("@", 1)[0]
    return local.replace("_", " ").replace(".", " ").title()


def _mentor_ui_tier(mp: MentorProfile) -> str:
    tid = (mp.tier_id or "PEER").upper()
    if tid in ("PEER", "PROFESSIONAL", "EXPERT"):
        return tid
    return "PEER"


def build_matchmaking_snapshot(db: Session) -> dict[str, Any]:
    """Read-only snapshot for AI service (mentor expertise + mentee goals)."""
    mentors: list[dict[str, Any]] = []
    for mp, email in (
        db.query(MentorProfile, User.email)
        .join(User, MentorProfile.user_id == User.id)
        .all()
    ):
        mentors.append(
            {
                "user_id": str(mp.user_id),
                "mentor_profile_id": str(mp.id),
                "expertise_areas": list(mp.expertise_areas or []),
                "is_accepting_requests": bool(mp.is_accepting_requests),
                "display_name": _display_name(email or ""),
                "tier": _mentor_ui_tier(mp),
                "session_credit_cost": resolve_mentor_session_price(db, mp),
                "headline": mp.headline or "",
                "bio": mp.bio or "",
                "current_title": mp.current_title or "",
                "current_company": mp.current_company or "",
                "years_experience": int(mp.years_experience) if mp.years_experience is not None else None,
                "professional_experiences": mp.professional_experiences or [],
            }
        )
    mentees: list[dict[str, Any]] = []
    for me, email in (
        db.query(MenteeProfile, User.email)
        .join(User, MenteeProfile.user_id == User.id)
        .all()
    ):
        mentees.append(
            {
                "user_id": str(me.user_id),
                "mentee_profile_id": str(me.id),
                "learning_goals": list(me.learning_goals or []),
                "education_level": me.education_level or "",
                "display_name": _display_name(email or ""),
            }
        )
    return {"mentors": mentors, "mentees": mentees}
