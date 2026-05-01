from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginRequest, LoginResponse, MeResponse
from app.services.profile_service import build_user_public

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
    is_admin = ("ADMIN" in (user.role or []))
    token = auth.create_token(user.user_id, user.email, user.role, is_admin=is_admin)
    return LoginResponse(
        access_token=token
    )


@router.get("/me", response_model=MeResponse)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return MeResponse(user=build_user_public(db, user=user))
