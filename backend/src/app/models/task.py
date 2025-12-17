"""
Task model
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class TaskAttachment(BaseModel):
    """Task attachment"""
    url: str
    name: str
    mime: str

class TaskComment(BaseModel):
    """Task comment"""
    comment_id: Optional[str] = Field(alias="_id", default=None)
    task_id: str
    content: str
    created_by: str  # user_id
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskActivityLog(BaseModel):
    """Task activity log (optional)"""
    task_id: str
    user_id: str
    action: str  # status_changed, assigned, comment_added, etc.
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    title: str
    description: Optional[str] = None
    status: str = Field(default="pending")  # pending | in_progress | completed
    priority: str = Field(default="medium")  # low | medium | high
    created_by: str  # user_id
    assigned_to: List[str] = Field(default_factory=list)  # List of user_ids
    watchers: List[str] = Field(default_factory=list)  # List of user_ids
    attachments: List[TaskAttachment] = Field(default_factory=list)
    comments: List[TaskComment] = Field(default_factory=list)
    org_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None

