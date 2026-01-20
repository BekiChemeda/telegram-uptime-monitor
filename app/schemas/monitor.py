from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class MonitorBase(BaseModel):
    url: str
    name: str
    interval_seconds: int = 60
    timeout_seconds: int = 10
    expected_status: int = 200
    is_active: bool = True

class MonitorCreate(MonitorBase):
    pass
class MonitorResponse(MonitorBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    last_checked: datetime | None

    class Config:
        from_attributes = True