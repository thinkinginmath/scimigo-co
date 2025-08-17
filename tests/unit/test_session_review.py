from datetime import datetime
from uuid import UUID, uuid4

import pytest
from co.db.models import Session as SessionModel
from co.services.sessions import SessionService


@pytest.mark.asyncio
async def test_record_success_calls_review(db_session, test_user_id):
    session = SessionModel(
        id=uuid4(),
        user_id=UUID(test_user_id),
        subject="coding",
        mode="practice",
        problem_id="p1",
        status="active",
        started_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(session)
    await db_session.commit()

    service = SessionService(db_session)
    await service.record_success(session.id)

    service.personalization.update_mastery.assert_awaited_once()
    service.personalization.mark_review_result.assert_awaited_once_with(
        user_id=session.user_id, problem_id="p1", success=True
    )


@pytest.mark.asyncio
async def test_record_failure_calls_review(db_session, test_user_id):
    session = SessionModel(
        id=uuid4(),
        user_id=UUID(test_user_id),
        subject="coding",
        mode="practice",
        problem_id="p2",
        status="active",
        started_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(session)
    await db_session.commit()

    service = SessionService(db_session)
    await service.record_failure(session.id, ["cat"])

    service.personalization.update_mastery.assert_awaited_once()
    service.personalization.mark_review_result.assert_awaited_once_with(
        user_id=session.user_id, problem_id="p2", success=False
    )
