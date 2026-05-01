from __future__ import annotations
from typing import Any
from sqlalchemy.orm import Session

def build_matchmaking_snapshot(db: Session) -> dict[str, Any]:
    """
    Read-only snapshot for AI service.
    In the new architecture, profile data is stored in the Mentoring Service.
    Returning empty snapshot from User Service.
    """
    return {"mentors": [], "mentees": []}
