from pydantic import BaseModel, HttpUrl, field_validator, validator
from datetime import datetime
from uuid import UUID
from typing import Optional
import re

class MonitorBase(BaseModel):
    url: HttpUrl
    name: str
    interval_seconds:  Optional[int] = 180
    timeout_seconds: Optional[int] = 10
    expected_status: Optional[int] = 200
    is_active: Optional[bool] = True
    
    # Pro Features
    check_ssl: Optional[bool] = False
    ssl_expiry_days_threshold: Optional[int] = 7
    keyword_include: Optional[str] = None
    keyword_exclude: Optional[str] = None
    max_response_time: Optional[float] = None # seconds
    consecutive_checks: Optional[int] = 3

    @field_validator('url', mode='before')
    @classmethod
    def validate_url(cls, v):
        if isinstance(v, str):
            # Strip whitespace
            v = v.strip()
            # If empty string, let Pydantic handle the error or not (depending on Optional)
            if not v:
                return v
            if not v.startswith(('http://', 'https://')):
                # Check if it looks like a domain (e.g., "example.com" or "example.com/foo")
                # We basically look for at least one dot in the beginning part before any slash
                # or verify it's localhost
                domain_regex = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d+)?(?:/.*)?$'
                # Also allow simple IP addresses
                ip_regex = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?(?:/.*)?$'
                
                if re.match(domain_regex, v) or re.match(ip_regex, v) or v.startswith("localhost"):
                   return f"https://{v}"
        return v

    @validator('interval_seconds')
    def interval_must_be_at_least_180(cls, v):
        if v is not None and v < 180:
            raise ValueError('Interval must be at least 180 seconds (3 minutes)')
        return v

class MonitorCreate(MonitorBase):
    telegram_id: int

class MonitorUpdate(BaseModel):
    telegram_id: int
    url: Optional[HttpUrl] = None
    name: Optional[str] = None
    interval_seconds: Optional[int] = None
    timeout_seconds: Optional[int] = None
    expected_status: Optional[int] = None
    is_active: Optional[bool] = None
    
    check_ssl: Optional[bool] = None
    ssl_expiry_days_threshold: Optional[int] = None
    keyword_include: Optional[str] = None
    keyword_exclude: Optional[str] = None
    max_response_time: Optional[float] = None
    consecutive_checks: Optional[int] = None

    @field_validator('url', mode='before')
    @classmethod
    def validate_url(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return v
            if not v.startswith(('http://', 'https://')):
                domain_regex = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d+)?(?:/.*)?$'
                ip_regex = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?(?:/.*)?$'
                
                if re.match(domain_regex, v) or re.match(ip_regex, v) or v.startswith("localhost"):
                   return f"https://{v}"
        return v
    
    @validator('interval_seconds')
    def interval_must_be_at_least_180(cls, v):
        if v is not None and v < 180:
            raise ValueError('Interval must be at least 180 seconds (3 minutes)')
        return v

class MonitorResponse(MonitorBase):
    id: UUID
    owner_id: UUID
    url: HttpUrl
    created_at: datetime
    last_checked: Optional[datetime] = None

    class Config:
        from_attributes = True