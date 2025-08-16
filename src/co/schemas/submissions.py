"""Submission-related schemas."""

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class CodingPayload(BaseModel):
    """Coding submission payload."""

    language: Literal["python", "javascript"]
    code: str


class MathPayload(BaseModel):
    """Math submission payload."""

    steps: Optional[List[str]] = None
    expression: Optional[str] = None


class SubmissionCodingCreate(BaseModel):
    """Create coding submission request."""

    session_id: UUID
    problem_id: str
    subject: Literal["coding"]
    payload: CodingPayload


class SubmissionMathCreate(BaseModel):
    """Create math submission request."""

    session_id: UUID
    problem_id: str
    subject: Literal["math"]
    payload: MathPayload


class VisibleResults(BaseModel):
    """Visible test results."""

    passed: int
    total: int
    details: List[Dict[str, Any]] = []


class HiddenResults(BaseModel):
    """Hidden test results."""

    passed: int
    total: int
    categories: List[str] = []


class SubmissionResult(BaseModel):
    """Submission evaluation result."""

    status: Literal["passed", "failed", "timeout", "error"]
    visible: VisibleResults
    hidden: HiddenResults
    exec_ms: int
