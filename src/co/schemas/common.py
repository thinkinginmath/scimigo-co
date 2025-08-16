"""Common Pydantic schemas."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Problem(BaseModel):
    """Problem schema."""

    id: str
    title: str
    content: str
    type: str
    difficulty: int = Field(ge=0, le=100)
    topics: List[str] = []
    visible_tests: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: Dict[str, Any] = Field(
        ...,
        examples=[
            {
                "code": "NOT_FOUND",
                "message": "Resource not found",
                "details": {},
            }
        ],
    )
