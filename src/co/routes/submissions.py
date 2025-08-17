"""Submission handling endpoints."""

from typing import Union
from uuid import UUID

from co.auth import get_current_user
from co.db.base import get_db
from co.schemas.submissions import (
    SubmissionCodingCreate,
    SubmissionMathCreate,
    SubmissionResult,
)
from co.services.evaluators.coding import CodingEvaluator
from co.services.evaluators.math import MathEvaluator
from co.services.sessions import SessionService
from co.services.study_task import StudyTaskService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("", response_model=SubmissionResult)
async def submit_attempt(
    submission: Union[SubmissionCodingCreate, SubmissionMathCreate],
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> SubmissionResult:
    """Submit an attempt for evaluation (subject-agnostic)."""
    # Verify session ownership
    session_service = SessionService(db)
    session = await session_service.get_session(submission.session_id)

    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    # Route to appropriate evaluator based on subject
    if submission.subject == "coding":
        coding_evaluator = CodingEvaluator(db)
        result = await coding_evaluator.evaluate(
            session_id=submission.session_id,
            problem_id=submission.problem_id,
            language=submission.payload.language,
            code=submission.payload.code,
            user_id=user_id,
        )
    elif submission.subject == "math":
        math_evaluator = MathEvaluator(db)
        result = await math_evaluator.evaluate(
            session_id=submission.session_id,
            problem_id=submission.problem_id,
            steps=submission.payload.steps,
            expression=submission.payload.expression,
            user_id=user_id,
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid subject")

    # Update session based on result
    if result.status == "passed":
        await session_service.record_success(submission.session_id)
    else:
        await session_service.record_failure(
            submission.session_id, result.hidden.categories
        )

    # Record evaluation for study task if provided
    task_id = getattr(submission, "task_id", None)
    if task_id:
        task_service = StudyTaskService(db)
        try:
            await task_service.record_evaluation(
                task_id=task_id,
                user_id=user_id,
                language=submission.payload.language
                if submission.subject == "coding"
                else None,
                code=submission.payload.code
                if submission.subject == "coding"
                else submission.payload.expression,
                result=result,
            )
        except ValueError:
            raise HTTPException(status_code=404, detail="Study task not found")

    return result


@router.get("/{submission_id}", response_model=SubmissionResult)
async def get_submission(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> SubmissionResult:
    """Get submission details."""
    # Implementation would fetch from database
    raise HTTPException(status_code=501, detail="Not implemented yet")
