"""GET /api/v1/search — mentor/mentee directory for Matchmaker (same contract as SPA)."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MenteeProfile, MentorProfile, User
from app.services.mentor_pricing import resolve_mentor_session_price

router = APIRouter()


class SearchResultItem(BaseModel):
    user_id: str
    mentor_profile_id: str | None = None
    full_name: str | None = None
    role: Literal["mentor", "mentee"]
    expertise: list[str] = Field(default_factory=list)
    tier: str | None = None
    session_credit_cost: int | None = Field(
        default=None,
        description="Mentors: credits per session (admin override or BOOK_MENTOR_SESSION base).",
    )



def _display_name(email: str) -> str:
    local = email.split("@", 1)[0]
    return local.replace("_", " ").replace(".", " ").title()


def _mentor_ui_tier(mp: MentorProfile) -> str:
    tid = (mp.tier_id or "PEER").upper()
    if tid in ("PEER", "PROFESSIONAL", "EXPERT"):
        return tid
    return "PEER"


@router.get("/search", response_model=list[SearchResultItem])
def search_directory(
    q: str = Query("", max_length=200),
    role: Literal["mentor", "mentee", "all"] = "mentor",
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[SearchResultItem]:
    term = q.strip()
    like = f"%{term}%" if term else None
    out: list[SearchResultItem] = []

    def mentor_slice(max_n: int) -> list[SearchResultItem]:
        qry = (
            db.query(MentorProfile, User.email)
            .join(User, MentorProfile.user_id == User.id)
            .filter(MentorProfile.is_accepting_requests.is_(True))
        )
        if like:
            qry = qry.filter(
                or_(
                    User.email.ilike(like),
                    func.coalesce(
                        func.array_to_string(MentorProfile.expertise_areas, " "),
                        "",
                    ).ilike(like),
                )
            )
        rows: list[SearchResultItem] = []
        for mp, email in qry.order_by(User.email).limit(max_n).all():
            expertise = list(mp.expertise_areas or [])
            rows.append(
                SearchResultItem(
                    user_id=str(mp.user_id),
                    mentor_profile_id=str(mp.id),
                    full_name=_display_name(email),
                    role="mentor",
                    expertise=expertise,
                    tier=_mentor_ui_tier(mp),
                    session_credit_cost=resolve_mentor_session_price(db, mp),
                )
            )

        return rows

    def mentee_slice(max_n: int) -> list[SearchResultItem]:
        qry = db.query(MenteeProfile, User.email).join(User, MenteeProfile.user_id == User.id)
        if like:
            qry = qry.filter(
                or_(
                    User.email.ilike(like),
                    func.coalesce(
                        func.array_to_string(MenteeProfile.learning_goals, " "),
                        "",
                    ).ilike(like),
                )
            )
        rows: list[SearchResultItem] = []
        for mep, email in qry.order_by(User.email).limit(max_n).all():
            expertise = list(mep.learning_goals or [])
            rows.append(
                SearchResultItem(
                    user_id=str(mep.user_id),
                    full_name=_display_name(email),
                    role="mentee",
                    expertise=expertise,
                    tier=None,
                )
            )
        return rows

    if role == "mentor":
        return mentor_slice(limit)
    if role == "mentee":
        return mentee_slice(limit)

    n_mentors = (limit + 1) // 2
    n_mentees = limit - n_mentors
    out.extend(mentor_slice(n_mentors))
    out.extend(mentee_slice(n_mentees))
    return out[:limit]
