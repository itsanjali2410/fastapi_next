"""
Chat schemas
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class MessageCreate(BaseModel):
    message: str

class MessageResponse(BaseModel):
    id: str
    sender_id: str
    sender_name: Optional[str] = None
    org_id: str
    message: str
    created_at: datetime
    is_read: bool

class ChatHistoryResponse(BaseModel):
    messages: List[MessageResponse]
    total: int

