import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, synonym

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    id = synonym("user_id")
    role: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=[])  # ['MENTOR', 'MENTEE', 'ADMIN']
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )
