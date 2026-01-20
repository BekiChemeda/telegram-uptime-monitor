from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None

class UserCreate(UserBase):
    created_at: Optional[datetime] = None

class UserResponse(UserBase):
    id: UUID
    joined_at: datetime
    class Config:
        from_attributes = True