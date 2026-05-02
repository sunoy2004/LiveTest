import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

class MentorshipRequestCreate(BaseModel):
    mentor_id: uuid.UUID = Field(..., alias="mentor_id")
    intro_message: str | None = None
    
    model_config = ConfigDict(populate_by_name=True)

class MentorshipRequestStatusUpdate(BaseModel):
    status: Literal["ACCEPTED", "DECLINED"] = Field(..., description="Accept or decline the pending request")

class MentorshipRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sender_user_id: uuid.UUID = Field(..., alias="mentee_user_id")
    receiver_user_id: uuid.UUID = Field(..., alias="mentor_user_id")
    status: str
    mentee_name: str | None = None
    mentor_name: str | None = None
