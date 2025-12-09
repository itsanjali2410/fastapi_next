"""
Invite link model
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class InviteLinkInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    org_id: str
    token: str  # unique token for each invite
    created_by: str  # admin user_id
    is_used: bool = False
    used_by: Optional[str] = None  # user_id who used it
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

