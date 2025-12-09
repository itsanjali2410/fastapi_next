"""
Task schemas
"""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: str
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    created_by: str
    assigned_to: str
    org_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None

