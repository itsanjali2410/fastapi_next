"""
User online/offline status and last seen tracking
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class UserStatusInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    is_online: bool = False
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

