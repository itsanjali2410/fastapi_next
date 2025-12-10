"""
Group chat schemas
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class GroupChatCreate(BaseModel):
    name: str
    description: Optional[str] = None
    member_ids: List[str]  # List of user IDs to add

class GroupChatUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None

class GroupChatMemberAdd(BaseModel):
    user_ids: List[str]

class GroupChatMemberRemove(BaseModel):
    user_id: str

class GroupChatResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    created_by: str
    created_by_name: Optional[str] = None
    members: List[str]
    member_names: List[str] = []
    admins: List[str] = []
    admin_names: List[str] = []
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

class GroupChatListItem(BaseModel):
    id: str
    name: str
    avatar_url: Optional[str] = None
    last_message: Optional[str] = None
    last_message_timestamp: Optional[datetime] = None
    unread_count: int = 0
    member_count: int = 0

class GroupChatListResponse(BaseModel):
    groups: List[GroupChatListItem]

