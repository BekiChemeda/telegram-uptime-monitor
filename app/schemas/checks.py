from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CheckLogBase(BaseModel):
    monitor_id: UUID
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    is_up: bool
    error_message: Optional[str] = None

class CheckLogCreate(CheckLogBase):
    pass

class CheckLogResponse(CheckLogBase):
    id: UUID
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)
