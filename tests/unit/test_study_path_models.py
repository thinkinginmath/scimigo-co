from datetime import datetime
from uuid import uuid4

from co.models import (
    StudyPath,
    StudyTask,
    TaskEvaluation,
    TaskEvent,
    TaskEventType,
    TaskStatus,
)


def test_study_path_models() -> None:
    path = StudyPath(user_id="user-123", track_id="coding-interview-meta")
    task = StudyTask(
        path=path,
        problem_id="two-sum",
        module="arrays-strings",
        difficulty=3,
        scheduled_at=datetime.utcnow(),
        status=TaskStatus.scheduled,
    )
    event = TaskEvent(task=task, event_type=TaskEventType.created)
    evaluation = TaskEvaluation(task=task, submission_id=uuid4(), language="python")

    assert task in path.tasks
    assert event in task.events
    assert evaluation in task.evaluations
    assert task.status is TaskStatus.scheduled
