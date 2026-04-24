from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationLogItem(BaseModel):
    id: UUID
    topic: str
    event_type: str
    created_at: datetime

    model_config = {"from_attributes": True}