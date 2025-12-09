"""
Organization model
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class OrgInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    name: str
    address: str
    no_of_users: int
    owner_name: str
    contact_number: str
    owner_id: str
    members: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

