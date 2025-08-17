"""Pydantic schemas for study tasks and review queue items."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from co.models import TaskStatus


class StudyTaskCreate(BaseModel):
    """Schema for creating a study task."""

    problem_id: str
    module: str
    topic_tags: List[str] = []
    difficulty: int
    scheduled_at: datetime
    meta: Dict[str, Any] = {}


class StudyTaskBatchCreate(BaseModel):
    """Request payload for creating multiple study tasks."""

    path_id: UUID
    tasks: List[StudyTaskCreate]


class StudyTask(BaseModel):
    """Study task representation."""

    id: UUID
    problem_id: str
    module: str
    topic_tags: List[str]
    difficulty: int
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus
    score: Optional[float] = None
    time_spent_seconds: Optional[int] = None
    hints_used: int
    meta: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class StudyTaskList(BaseModel):
    """List of study tasks."""

    items: List[StudyTask]


class ReviewItem(BaseModel):
    """Due review queue item."""

    problem_id: str
    reason: str
    next_due_at: datetime
    bucket: int

    class Config:
        from_attributes = True


class ReviewList(BaseModel):
    """Collection of due review items."""

    items: List[ReviewItem]
