"""
ConversationParticipant model - Unified inbox model for DMs and Groups
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ConversationParticipant(BaseModel):
    """
    Represents a user's view of a conversation (DM or Group).
    Used for unified inbox functionality.
    """
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    user_id: str
    conversation_id: str
    type: str  # "dm" or "group"
    name: str
    last_message_content: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    image: Optional[str] = None
    other_user_id: Optional[str] = None  # For DMs: the other user's ID
    group_id: Optional[str] = None  # For groups: the group chat ID


