"""Session-related schemas."""

from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SessionCreate(BaseModel):
    """Create session request."""
    subject: Literal["coding", "math", "systems"]
    mode: Literal["practice", "mock", "track"]
    track_id: Optional[UUID] = None
    problem_id: Optional[str] = None


class SessionUpdate(BaseModel):
    """Update session request."""
    action: Literal["advance", "retry", "giveup"]


class Session(BaseModel):
    """Session response."""
    id: UUID
    user_id: UUID
    subject: str
    mode: str
    track_id: Optional[UUID] = None
    problem_id: Optional[str] = None
    status: str
    last_hint_level: int
    started_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True