import pytest
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from co.models import StudyPath, StudyTask, TaskEvaluation, TaskStatus
from co.services.study_task import StudyTaskService
from co.schemas.submissions import SubmissionResult, VisibleResults, HiddenResults


@pytest.mark.asyncio
async def test_record_evaluation_updates_task_and_review(db_session, test_user_id):
    path = StudyPath(user_id=test_user_id, track_id="track1", config={})
    db_session.add(path)
    await db_session.commit()
    await db_session.refresh(path)

    task = StudyTask(
        path_id=path.id,
        problem_id="prob-1",
        module="arrays",
        topic_tags=[],
        difficulty=1,
        scheduled_at=datetime.utcnow(),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    result = SubmissionResult(
        status="failed",
        visible=VisibleResults(passed=0, total=1, details=[]),
        hidden=HiddenResults(passed=0, total=1, categories=["logic_error"]),
        exec_ms=10,
    )

    service = StudyTaskService(db_session)
    await service.record_evaluation(
        task_id=task.id,
        user_id=UUID(test_user_id),
        language="python",
        code="print(1)",
        result=result,
    )

    await db_session.refresh(task)
    assert task.status == TaskStatus.completed
    assert task.score == 0.0

    query = await db_session.execute(
        select(TaskEvaluation).where(TaskEvaluation.task_id == task.id)
    )
    evaluation = query.scalar_one()
    assert evaluation.test_cases_total == 2
    assert evaluation.test_cases_passed == 0

    service.personalization.mark_review_result.assert_awaited_once()
