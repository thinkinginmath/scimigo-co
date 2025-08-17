import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4

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


@pytest.mark.asyncio
async def test_get_next_task_returns_earliest(db_session, test_user_id):
    path = StudyPath(user_id=test_user_id, track_id="track1", config={})
    db_session.add(path)
    await db_session.commit()
    await db_session.refresh(path)

    early = StudyTask(
        path_id=path.id,
        problem_id="p1",
        module="arrays",
        topic_tags=[],
        difficulty=1,
        scheduled_at=datetime.utcnow(),
    )
    late = StudyTask(
        path_id=path.id,
        problem_id="p2",
        module="arrays",
        topic_tags=[],
        difficulty=1,
        scheduled_at=datetime.utcnow().replace(microsecond=0) + timedelta(hours=1),
    )
    db_session.add_all([early, late])
    await db_session.commit()

    service = StudyTaskService(db_session)
    task = await service.get_next_task(UUID(test_user_id))
    assert task.id == early.id


@pytest.mark.asyncio
async def test_get_user_tasks_filters(db_session):
    user_id = str(uuid4())
    path = StudyPath(user_id=user_id, track_id="track1", config={})
    db_session.add(path)
    await db_session.commit()
    await db_session.refresh(path)

    task1 = StudyTask(
        path_id=path.id,
        problem_id="p1",
        module="arrays",
        topic_tags=[],
        difficulty=1,
        scheduled_at=datetime.utcnow(),
    )
    task2 = StudyTask(
        path_id=path.id,
        problem_id="p2",
        module="graphs",
        topic_tags=[],
        difficulty=1,
        scheduled_at=datetime.utcnow(),
        status=TaskStatus.completed,
    )
    db_session.add_all([task1, task2])
    await db_session.commit()

    service = StudyTaskService(db_session)
    tasks = await service.get_user_tasks(UUID(user_id), module="arrays")
    assert len(tasks) == 1
    assert tasks[0].module == "arrays"
