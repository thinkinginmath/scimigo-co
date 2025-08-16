"""Study task model."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from co.db.base import Base

# JSONB for Postgres with JSON fallback
JSONType = JSON().with_variant(JSONB, "postgresql")


class TaskStatus(enum.Enum):
    """Lifecycle status of a study task."""

    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"
    expired = "expired"


class StudyTask(Base):
    """Individual study task."""

    __tablename__ = "study_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    path_id = Column(
        UUID(as_uuid=True),
        ForeignKey("study_paths.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_id = Column(String(100), nullable=False)
    module = Column(String(50), nullable=False)
    topic_tags = Column(JSONType, nullable=False, default=list)
    difficulty = Column(Integer, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.scheduled,
    )
    score = Column(Float, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)
    hints_used = Column(Integer, nullable=False, default=0)
    meta = Column("metadata", JSONType, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    path = relationship("StudyPath", back_populates="tasks")
    events = relationship(
        "TaskEvent", back_populates="task", cascade="all, delete-orphan"
    )
    evaluations = relationship(
        "TaskEvaluation", back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="check_difficulty"),
        Index("idx_study_tasks_path_schedule", "path_id", "scheduled_at"),
        Index("idx_study_tasks_path_module_status", "path_id", "module", "status"),
        Index("idx_study_tasks_problem", "problem_id"),
    )
