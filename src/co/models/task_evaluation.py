"""Task evaluation model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from co.db.base import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class TaskEvaluation(Base):
    """Evaluation results for a study task submission."""

    __tablename__ = "task_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("study_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    submission_id = Column(
        UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=True
    )
    language = Column(String(50), nullable=True)
    code = Column(Text, nullable=True)
    test_cases_passed = Column(Integer, nullable=False, default=0)
    test_cases_total = Column(Integer, nullable=False, default=0)
    runtime_ms = Column(Integer, nullable=True)
    memory_mb = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    meta = Column("metadata", JSONType, nullable=False, default=dict)

    task = relationship("StudyTask", back_populates="evaluations")

    __table_args__ = (Index("idx_task_eval_task", "task_id", "created_at"),)
