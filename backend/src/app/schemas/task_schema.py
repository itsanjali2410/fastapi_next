"""
Task schemas for request/response models
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class TaskAttachmentSchema(BaseModel):
    url: str
    name: str
    mime: str

class TaskCommentSchema(BaseModel):
    comment_id: Optional[str] = None
    task_id: str
    content: str
    created_by: str
    created_by_name: Optional[str] = None
    created_at: datetime

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    assigned_to: List[str] = []
    watchers: List[str] = []
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[List[str]] = None
    watchers: Optional[List[str]] = None
    due_date: Optional[datetime] = None

class TaskStatusUpdate(BaseModel):
    status: str  # pending | in_progress | completed

class TaskCommentCreate(BaseModel):
    content: str

class TaskAssignRequest(BaseModel):
    user_ids: List[str]

class TaskWatchRequest(BaseModel):
    watch: bool = True  # True to watch, False to unwatch

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    created_by: str
    created_by_name: Optional[str] = None
    assigned_to: List[str]
    assigned_to_names: Optional[List[str]] = None
    watchers: List[str]
    watchers_names: Optional[List[str]] = None
    attachments: List[TaskAttachmentSchema] = []
    comments: List[TaskCommentSchema] = []
    org_id: str
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None
