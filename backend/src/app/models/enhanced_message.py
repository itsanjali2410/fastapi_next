"""
Enhanced Message model with reply, edit, delete, reactions, and delivery status
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class MessageReaction(BaseModel):
    """Reaction on a message"""
    user_id: str
    emoji: str  # e.g., "👍", "❤️", "😂"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MessageDeliveryStatus(BaseModel):
    """Delivery and read status for a message"""
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    read: bool = False
    read_at: Optional[datetime] = None
    read_by: Optional[str] = None  # user_id who read it

class EnhancedMessageInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    organization_id: str
    sender_id: str
    receiver_id: Optional[str] = None  # For 1-to-1 chats
    group_chat_id: Optional[str] = None  # For group chats
    content: str
    reply_to: Optional[str] = None  # Message ID this is replying to
    edited: bool = False
    edited_at: Optional[datetime] = None
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    reactions: List[MessageReaction] = Field(default_factory=list)
    delivery_status: Dict[str, MessageDeliveryStatus] = Field(default_factory=dict)  # Key: user_id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

