"""
Chat/Message model
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class MessageInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    sender_id: str  # user_id
    org_id: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = False

