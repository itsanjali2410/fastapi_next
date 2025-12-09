"""
Organization schemas for request/response validation
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class OrgCreate(BaseModel):
    name: str
    address: str
    no_of_users: int
    owner_name: str
    contact_number: str

class OrgUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    no_of_users: Optional[int] = None
    owner_name: Optional[str] = None
    contact_number: Optional[str] = None

class OrgResponse(BaseModel):
    id: str
    name: str
    address: str
    no_of_users: int
    owner_name: str
    contact_number: str
    owner_id: str
    members: List[str] = []
    created_at: datetime
    updated_at: datetime
    is_active: bool

class OrgWithMembers(OrgResponse):
    member_count: int

    class Config:
        populate_by_name = True
