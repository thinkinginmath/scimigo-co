"""Service for managing study tasks and evaluations."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from co.models import (
    StudyPath,
    StudyTask,
    TaskEvaluation,
    TaskEvent,
    TaskEventType,
    TaskStatus,
)
from co.schemas.study_tasks import StudyTaskCreate
from co.schemas.submissions import SubmissionResult
from co.services.personalization import PersonalizationService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class StudyTaskService:
    """Operations related to study tasks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.personalization = PersonalizationService(db)

    async def create_tasks_batch(
        self, user_id: UUID, path_id: UUID, tasks: list[StudyTaskCreate]
    ) -> list[StudyTask]:
        """Create a batch of study tasks for the specified path."""
        path = await self.db.get(StudyPath, path_id)
        if not path or path.user_id != str(user_id):
            raise ValueError("Study path not found")

        created: list[StudyTask] = []
        for data in tasks:
            task = StudyTask(
                path_id=path_id,
                problem_id=data.problem_id,
                module=data.module,
                topic_tags=data.topic_tags,
                difficulty=data.difficulty,
                scheduled_at=data.scheduled_at,
                meta=data.meta,
            )
            self.db.add(task)
            event = TaskEvent(task=task, event_type=TaskEventType.created, payload={})
            self.db.add(event)
            created.append(task)

        await self.db.commit()
        for task in created:
            await self.db.refresh(task)
        return created

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
        query = (
            select(StudyTask).join(StudyPath).where(StudyPath.user_id == str(user_id))
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

        t = cast(Any, task)
        t.status = TaskStatus.completed
        t.score = score
        t.completed_at = datetime.utcnow()

        event = TaskEvent(
            task_id=task.id,
            event_type=TaskEventType.evaluated,
            payload={"status": result.status, "score": score},
        )
        self.db.add(event)

        await self.personalization.mark_review_result(
            user_id=user_id,
            problem_id=cast(str, task.problem_id),
            success=result.status == "passed",
        )

        await self.db.commit()
        await self.db.refresh(evaluation)
        await self.db.refresh(task)
        return evaluation
