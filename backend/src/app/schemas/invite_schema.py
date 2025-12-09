"""
Invite link schemas
"""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class InviteLinkCreate(BaseModel):
    expires_at: Optional[datetime] = None

class InviteLinkResponse(BaseModel):
    id: str
    org_id: str
    token: str
    invite_url: str
    created_by: str
    is_used: bool
    used_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

class InviteLinkUse(BaseModel):
    token: str
    email: str
    password: str
    name: str

