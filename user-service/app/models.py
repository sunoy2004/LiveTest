import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import synonym

from app.db import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = synonym("user_id")
    email = Column(Text, unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(ARRAY(Text), nullable=False, default=[])  # ['MENTOR', 'MENTEE', 'ADMIN']
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
