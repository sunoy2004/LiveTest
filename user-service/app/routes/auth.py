from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import (
    DashboardStatsResponse,
    FullProfileResponse,
    GoalItem,
    LoginRequest,
    LoginResponse,
    MeResponse,
    UpcomingSessionItem,
    UpcomingSessionResponse,
    UserPublic,
    VaultItem,
)
from app.services.dashboard_service import (
    get_dashboard_stats,
    get_goals,
    get_upcoming_session,
    get_upcoming_sessions,
    get_vault,
)
from app.services.profile_service import build_user_public, get_full_profile

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if not user or not auth.verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    # Check if admin
    is_admin = (user.role == "ADMIN")
    token = auth.create_token(user.user_id, user.email, user.role, is_admin=is_admin)
    return LoginResponse(
        access_token=token
    )


@router.get("/me", response_model=MeResponse)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return MeResponse(user=build_user_public(db, user=user))
