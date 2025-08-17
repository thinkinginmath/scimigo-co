import pytest
from co.services.study_path import StudyPathService


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value, ex=None):
        self.store[key] = value


@pytest.mark.asyncio
async def test_create_and_get_active_path(db_session):
    service = StudyPathService(db_session)
    service._redis = FakeRedis()
    path = await service.create_study_path("user-1", "track-1", {"level": 1})

    cached = await service._redis.get("study_path:active:user-1")
    assert cached is not None

    # Remove from DB to force cache usage
    await db_session.delete(path)
    await db_session.commit()

    cached_path = await service.get_active_path("user-1")
    assert cached_path is not None
    assert cached_path.id == path.id
    assert cached_path.config["level"] == 1


@pytest.mark.asyncio
async def test_update_path_config(db_session):
    service = StudyPathService(db_session)
    service._redis = FakeRedis()

    path = await service.create_study_path("user-1", "track-1", {"level": 1})
    updated = await service.update_path_config(path.id, {"level": 2})
    assert updated.config["level"] == 2

    cached_path = await service.get_active_path("user-1")
    assert cached_path.config["level"] == 2
