"""
Group Chat models
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class GroupChatInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    organization_id: str
    name: str
    description: Optional[str] = None
    created_by: str  # user_id
    members: List[str]  # List of user_ids
    admins: List[str]  # List of admin user_ids
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


