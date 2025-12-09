"""
Task model
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class TaskInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    title: str
    description: Optional[str] = None
    created_by: str  # user_id
    assigned_to: str  # user_id
    org_id: str
    status: str = Field(default="pending")  # pending, in_progress, completed, cancelled
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None

