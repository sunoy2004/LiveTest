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
    pub = build_user_public(db, user=user)
    token = auth.create_token(user.id, is_admin=pub.is_admin)
    return LoginResponse(
        token=token,
        user=pub,
    )


@router.get("/me", response_model=MeResponse)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return MeResponse(user=build_user_public(db, user=user))


@router.get("/profile/full", response_model=FullProfileResponse)
def profile_full(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_full_profile(db, user=user)


def _parse_dashboard_context(context: str | None) -> str | None:
    if context is None:
        return None
    c = context.strip().lower()
    if c not in ("mentor", "mentee"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="context must be 'mentor' or 'mentee'",
        )
    return c


@router.get("/dashboard/upcoming-session", response_model=UpcomingSessionResponse)
async def dashboard_upcoming_session(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    context: str | None = Query(None),
):
    ctx = _parse_dashboard_context(context)
    raw = await get_upcoming_session(db, user=user, context=ctx)
    if not raw:
        return UpcomingSessionResponse()
    return UpcomingSessionResponse.model_validate(raw)


@router.get("/dashboard/upcoming-sessions", response_model=list[UpcomingSessionItem])
async def dashboard_upcoming_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    context: str | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
):
    ctx = _parse_dashboard_context(context)
    rows = await get_upcoming_sessions(db, user=user, context=ctx, limit=limit)
    return [UpcomingSessionItem.model_validate(r) for r in rows]


@router.get("/dashboard/goals", response_model=list[GoalItem])
async def dashboard_goals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    context: str | None = Query(None),
):
    ctx = _parse_dashboard_context(context)
    rows = await get_goals(db, user=user, context=ctx)
    return [GoalItem.model_validate(r) for r in rows]


@router.get("/dashboard/vault", response_model=list[VaultItem])
async def dashboard_vault(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    context: str | None = Query(None),
):
    ctx = _parse_dashboard_context(context)
    rows = await get_vault(db, user=user, context=ctx)
    return [VaultItem.model_validate(r) for r in rows]


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    context: str | None = Query(None),
):
    ctx = _parse_dashboard_context(context)
    raw = await get_dashboard_stats(db, user=user, context=ctx)
    return DashboardStatsResponse.model_validate(raw)
