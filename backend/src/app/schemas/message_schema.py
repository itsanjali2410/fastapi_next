"""
Message schemas for request/response models
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    receiver_id: str
    content: str

class MessageResponse(BaseModel):
    """Schema for message response"""
    id: str
    organization_id: str
    sender_id: str
    receiver_id: str
    content: str
    created_at: datetime
    is_read: bool
    sender_name: Optional[str] = None
    receiver_name: Optional[str] = None
    reply_to: Optional[str] = None
    reply_to_content: Optional[str] = None
    edited: Optional[bool] = False
    edited_at: Optional[datetime] = None
    deleted: Optional[bool] = False
    reactions: Optional[List[dict]] = None
    delivery_status: Optional[dict] = None
    group_chat_id: Optional[str] = None

class MessageHistoryResponse(BaseModel):
    """Schema for message history response"""
    messages: List[MessageResponse]
    total: int
    has_more: bool = False

class ChatListItem(BaseModel):
    """Schema for chat list item (WhatsApp-like)"""
    other_user_id: str
    other_user_name: str
    last_message: Optional[str] = None
    last_message_timestamp: Optional[datetime] = None
    unread_count: int = 0

class ChatListResponse(BaseModel):
    """Schema for chat list response"""
    chats: List[ChatListItem]

class UserListItem(BaseModel):
    """Schema for user list item"""
    id: str
    name: str
    email: str

class UserListResponse(BaseModel):
    """Schema for user list response"""
    users: List[UserListItem]


