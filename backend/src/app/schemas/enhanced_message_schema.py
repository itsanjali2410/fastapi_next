"""
Enhanced message schemas with reply, edit, delete, reactions
"""
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime

class MessageReactionSchema(BaseModel):
    user_id: str
    emoji: str
    created_at: datetime

class MessageDeliveryStatusSchema(BaseModel):
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    read: bool = False
    read_at: Optional[datetime] = None
    read_by: Optional[str] = None

class EnhancedMessageCreate(BaseModel):
    receiver_id: Optional[str] = None  # For 1-to-1
    group_chat_id: Optional[str] = None  # For group
    content: str
    reply_to: Optional[str] = None  # Message ID

class EnhancedMessageResponse(BaseModel):
    id: str
    organization_id: str
    sender_id: str
    receiver_id: Optional[str] = None
    group_chat_id: Optional[str] = None
    content: str
    reply_to: Optional[str] = None
    reply_to_content: Optional[str] = None  # Content of replied message
    edited: bool = False
    edited_at: Optional[datetime] = None
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    reactions: List[MessageReactionSchema] = []
    delivery_status: Dict[str, MessageDeliveryStatusSchema] = {}
    created_at: datetime
    updated_at: datetime
    sender_name: Optional[str] = None

class MessageEditRequest(BaseModel):
    content: str

class MessageReactionRequest(BaseModel):
    emoji: str

class MessageHistoryEnhancedResponse(BaseModel):
    messages: List[EnhancedMessageResponse]
    total: int
    has_more: bool = False


