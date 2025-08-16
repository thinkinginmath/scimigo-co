"""Study path model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from co.db.base import Base

# JSONB for Postgres with JSON fallback
JSONType = JSON().with_variant(JSONB, "postgresql")


class StudyPath(Base):
    """Personalized study path for a user."""

    __tablename__ = "study_paths"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False)
    track_id = Column(String(100), nullable=False, default="coding-interview-meta")
    config = Column(JSONType, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    tasks = relationship(
        "StudyTask",
        back_populates="path",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (Index("idx_study_paths_user", "user_id", "created_at"),)
