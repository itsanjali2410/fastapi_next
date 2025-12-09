from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic import Field, ConfigDict

class MessageInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    organization_id: str
    sender_id: str
    receiver_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = False


