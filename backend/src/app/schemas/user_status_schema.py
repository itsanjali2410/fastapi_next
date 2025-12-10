"""
User status schemas
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class UserStatusResponse(BaseModel):
    user_id: str
    is_online: bool
    last_seen: datetime
    user_name: Optional[str] = None

class UserStatusUpdate(BaseModel):
    is_online: bool

class UsersStatusResponse(BaseModel):
    statuses: List[UserStatusResponse]

