"""Tutor-related schemas."""

from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class TutorMessageCreate(BaseModel):
    """Create tutor message request."""
    session_id: UUID
    problem_id: str
    hint_level: int = Field(ge=1, le=3)
    last_eval: Optional[Dict[str, Any]] = None


class TutorStreamResponse(BaseModel):
    """Tutor stream response."""
    stream_url: str
    token: str