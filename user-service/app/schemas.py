from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    """Credentials identity from `users` row (includes `users.role` for shell / MFE UI)."""

    id: UUID
    email: str
    is_admin: bool = False
    roles: list[str] = []

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str


class MeResponse(BaseModel):
    user: UserPublic
