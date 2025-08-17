"""Task event model."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from co.db.base import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class TaskEventType(enum.Enum):
    """Types of events in task lifecycle."""

    created = "created"
    started = "started"
    submitted = "submitted"
    evaluated = "evaluated"
    hint_requested = "hint_requested"
    tutor_interaction = "tutor_interaction"
    status_changed = "status_changed"


class TaskEvent(Base):
    """Event log for study tasks."""

    __tablename__ = "task_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("study_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[TaskEventType] = mapped_column(
        Enum(TaskEventType, name="task_event_type"), nullable=False
    )
    payload = Column(JSONType, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    task = relationship("StudyTask", back_populates="events")

    __table_args__ = (Index("idx_task_events_task", "task_id", "created_at"),)
