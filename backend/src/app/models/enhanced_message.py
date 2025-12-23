from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class MessageDeliveryStatus(BaseModel):
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    read: bool = False
    read_at: Optional[datetime] = None


class EnhancedMessageInDB(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(alias="_id", default=None)
    organization_id: str

    chat_type: str = "personal"  # personal | group
    sender_id: str

    receiver_id: Optional[str] = None
    group_chat_id: Optional[str] = None

    content: str
    type: str = "text"

    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    mime_type: Optional[str] = None

    reply_to: Optional[str] = None

    edited: bool = False
    edited_at: Optional[datetime] = None

    deleted: bool = False
    deleted_at: Optional[datetime] = None

    # ✅ 1–1 chat only
    delivery_status: Dict[str, MessageDeliveryStatus] = Field(default_factory=dict)

    # ✅ group chat only
    read_by: List[str] = Field(default_factory=list)
    # Mapping of user_id -> datetime when they read the message
    read_by_details: Dict[str, datetime] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
