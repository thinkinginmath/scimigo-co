"""SQLAlchemy ORM models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text,
    ForeignKey, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from co.db.base import Base


class Track(Base):
    """Track/curriculum model."""
    __tablename__ = "tracks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    slug = Column(String, unique=True, nullable=False)
    subject = Column(String, nullable=False)
    title = Column(Text, nullable=False)
    labels = Column(JSONB, nullable=False, default=list)
    modules = Column(JSONB, nullable=False, default=list)
    version = Column(String, nullable=False, default="v1")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="track")
    
    __table_args__ = (
        CheckConstraint("subject IN ('coding', 'math', 'systems')", name="check_subject"),
    )


class Session(Base):
    """Learning session model."""
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    subject = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=True)
    problem_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    last_hint_level = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    track = relationship("Track", back_populates="sessions")
    submissions = relationship("Submission", back_populates="session")
    
    __table_args__ = (
        CheckConstraint("subject IN ('coding', 'math', 'systems')", name="check_session_subject"),
        CheckConstraint("mode IN ('practice', 'mock', 'track')", name="check_mode"),
        Index("idx_sessions_user", "user_id"),
        Index("idx_sessions_track", "track_id"),
    )


class Submission(Base):
    """Submission/attempt model."""
    __tablename__ = "submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    problem_id = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    language = Column(String, nullable=True)
    status = Column(String, nullable=False)
    visible_passed = Column(Integer, nullable=False, default=0)
    visible_total = Column(Integer, nullable=False, default=0)
    hidden_passed = Column(Integer, nullable=False, default=0)
    hidden_total = Column(Integer, nullable=False, default=0)
    categories = Column(JSONB, nullable=False, default=list)
    exec_ms = Column(Integer, nullable=False, default=0)
    payload_sha256 = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="submissions")
    rubric_scores = relationship("RubricScore", back_populates="submission")
    
    __table_args__ = (
        CheckConstraint("subject IN ('coding', 'math', 'systems')", name="check_submission_subject"),
        CheckConstraint("status IN ('passed', 'failed', 'timeout', 'error')", name="check_status"),
        Index("idx_submissions_session", "session_id"),
        Index("idx_submissions_user", "user_id"),
        Index("idx_submissions_problem", "problem_id"),
    )


class Mastery(Base):
    """Mastery tracking model."""
    __tablename__ = "mastery"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    key_type = Column(String, primary_key=True)
    key_id = Column(String, primary_key=True)
    score = Column(Integer, nullable=False)
    ema = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("key_type IN ('topic', 'outcome')", name="check_key_type"),
        CheckConstraint("score >= 0 AND score <= 100", name="check_score_range"),
        Index("idx_mastery_user", "user_id"),
    )


class ReviewQueue(Base):
    """Spaced repetition review queue."""
    __tablename__ = "review_queue"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    problem_id = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    next_due_at = Column(DateTime(timezone=True), nullable=False)
    bucket = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="unique_user_problem"),
        Index("idx_review_due", "next_due_at"),
    )


class Rubric(Base):
    """Rubric for LLM-graded assessments."""
    __tablename__ = "rubrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain = Column(String, nullable=False)
    title = Column(Text, nullable=False)
    dimensions = Column(JSONB, nullable=False)
    metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    scores = relationship("RubricScore", back_populates="rubric")


class RubricScore(Base):
    """Rubric scores per submission."""
    __tablename__ = "rubric_scores"
    
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), primary_key=True)
    rubric_id = Column(UUID(as_uuid=True), ForeignKey("rubrics.id"), primary_key=True)
    scores = Column(JSONB, nullable=False)
    feedback = Column(JSONB, nullable=False)
    
    # Relationships
    submission = relationship("Submission", back_populates="rubric_scores")
    rubric = relationship("Rubric", back_populates="scores")