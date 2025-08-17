"""Service for managing study tasks and evaluations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from co.models import (
    StudyPath,
    StudyTask,
    TaskEvaluation,
    TaskEvent,
    TaskEventType,
    TaskStatus,
)
from co.schemas.submissions import SubmissionResult
from co.services.personalization import PersonalizationService


class StudyTaskService:
    """Operations related to study tasks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.personalization = PersonalizationService(db)

    async def get_next_task(self, user_id: UUID) -> StudyTask | None:
        """Get the next scheduled study task for a user."""
        result = await self.db.execute(
            select(StudyTask)
            .join(StudyPath)
            .where(
                StudyPath.user_id == str(user_id),
                StudyTask.status == TaskStatus.scheduled,
            )
            .order_by(StudyTask.scheduled_at)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_user_tasks(
        self,
        user_id: UUID,
        *,
        module: str | None = None,
        status: TaskStatus | None = None,
        limit: int = 20,
    ) -> list[StudyTask]:
        """List study tasks for a user with optional filters."""
        query = select(StudyTask).join(StudyPath).where(
            StudyPath.user_id == str(user_id)
        )

        if module:
            query = query.where(StudyTask.module == module)
        if status:
            query = query.where(StudyTask.status == status)

        result = await self.db.execute(
            query.order_by(StudyTask.scheduled_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def record_evaluation(
        self,
        task_id: UUID,
        user_id: UUID,
        language: str | None,
        code: str | None,
        result: SubmissionResult,
    ) -> TaskEvaluation:
        """Record evaluation result for a study task."""
        task = await self.db.get(StudyTask, task_id)
        if not task:
            raise ValueError("Task not found")
        # Validate ownership
        if task.path.user_id != str(user_id):
            raise ValueError("Task does not belong to user")

        total_tests = result.visible.total + result.hidden.total
        passed_tests = result.visible.passed + result.hidden.passed
        score = passed_tests / total_tests if total_tests else 0.0

        evaluation = TaskEvaluation(
            task_id=task.id,
            language=language,
            code=code,
            test_cases_passed=passed_tests,
            test_cases_total=total_tests,
            runtime_ms=result.exec_ms,
            error_message=None if result.status == "passed" else result.status,
            meta={"categories": result.hidden.categories},
        )
        self.db.add(evaluation)

        task.status = TaskStatus.completed
        task.score = score
        task.completed_at = datetime.utcnow()

        event = TaskEvent(
            task_id=task.id,
            event_type=TaskEventType.evaluated,
            payload={"status": result.status, "score": score},
        )
        self.db.add(event)

        await self.personalization.mark_review_result(
            user_id=user_id, problem_id=task.problem_id, success=result.status == "passed"
        )

        await self.db.commit()
        await self.db.refresh(evaluation)
        await self.db.refresh(task)
        return evaluation
