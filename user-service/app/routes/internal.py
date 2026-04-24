import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.matchmaking_snapshot import build_matchmaking_snapshot

router = APIRouter(tags=["internal"])

INTERNAL_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")


def require_internal_token(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
) -> None:
    if not INTERNAL_TOKEN or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid internal token")


@router.get("/matchmaking/snapshot")
def matchmaking_snapshot(
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
):
    return build_matchmaking_snapshot(db)

@router.get("/users/names")
def internal_user_names(
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
):
    from app.models import User
    rows = db.query(User.id, User.email).all()
    # display name from email
    def _display_name(email: str) -> str:
        local = email.split("@", 1)[0]
        return local.replace("_", " ").replace(".", " ").title()
        
    return {str(r.id): _display_name(r.email) for r in rows}
