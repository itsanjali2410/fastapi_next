from typing import Optional
from pydantic import BaseModel, Field, EmailStr, ConfigDict

class UserInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(alias="_id", default=None)
    email: EmailStr
    hashed_password: str
    name: str
    role: str = Field(default="user")
    org_id: Optional[str] = None 
    org_name: Optional[str] = None
    is_active: bool = True