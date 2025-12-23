"""
ConversationParticipant model - Unified inbox model for DMs and Groups
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ConversationParticipant(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    user_id: str
    conversation_id: str
    type: str 
    name: str
    last_message_content: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    last_seen_message_id: Optional[str] = None
    unread_count: Optional[int] = None
    image: Optional[str] = None
    other_user_id: Optional[str] = None  
    group_id: Optional[str] = None  # For groups: the group chat ID


