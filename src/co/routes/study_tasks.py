"""Endpoints for study task retrieval and review queue."""

from uuid import UUID

from co.auth import get_current_user
from co.db.base import get_db
from co.schemas.study_tasks import (
    ReviewList,
    StudyTaskBatchCreate,
    StudyTaskList,
)
from co.schemas.study_tasks import (
    StudyTask as StudyTaskSchema,
)
from co.services.personalization import PersonalizationService
from co.services.study_task import StudyTaskService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/batch", response_model=StudyTaskList)
async def create_task_batch(
    payload: StudyTaskBatchCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> StudyTaskList:
    """Create a batch of study tasks for a study path."""
    service = StudyTaskService(db)
    tasks = await service.create_tasks_batch(user_id, payload.path_id, payload.tasks)
    return StudyTaskList(items=tasks)


@router.get("/next", response_model=StudyTaskSchema)
async def get_next_task(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> StudyTaskSchema:
    """Get the next scheduled study task for the authenticated user."""
    service = StudyTaskService(db)
    task = await service.get_next_task(user_id)
    if not task:
        raise HTTPException(status_code=404, detail="No scheduled tasks")
    return task


@router.get("", response_model=StudyTaskList)
async def list_tasks(
    module: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> StudyTaskList:
    """List study tasks for the user with optional filters."""
    service = StudyTaskService(db)
    status_enum = None
    if status:
        try:
            from co.models import TaskStatus

            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    tasks = await service.get_user_tasks(
        user_id, module=module, status=status_enum, limit=limit
    )
    return StudyTaskList(items=tasks)


@router.get("/review-due", response_model=ReviewList)
async def get_due_reviews(
    limit: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
) -> ReviewList:
    """Return review queue items that are due for the user."""
    service = PersonalizationService(db)
    items = await service.get_due_reviews(user_id, limit=limit)
    return ReviewList(items=items)
