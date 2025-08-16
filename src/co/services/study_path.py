"""Study path service layer."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from redis import asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from co.config import get_settings
from co.models import StudyPath


class StudyPathService:
    """Service for managing study paths."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        if not self._redis:
            self._redis = await aioredis.from_url(self.settings.redis_url)
        return self._redis

    def _cache_key(self, user_id: str) -> str:
        return f"study_path:active:{user_id}"

    async def create_study_path(
        self, user_id: str, track_id: str, config: dict
    ) -> StudyPath:
        """Create a new study path and cache it as active."""
        path = StudyPath(user_id=user_id, track_id=track_id, config=config)
        self.db.add(path)
        await self.db.commit()
        await self.db.refresh(path)

        redis = await self._get_redis()
        await redis.set(self._cache_key(user_id), json.dumps(self._serialize(path)))
        return path

    async def get_active_path(self, user_id: str) -> Optional[StudyPath]:
        """Get the user's active study path using Redis cache."""
        redis = await self._get_redis()
        cached = await redis.get(self._cache_key(user_id))
        if cached:
            return self._deserialize(cached)

        result = await self.db.execute(
            select(StudyPath)
            .where(StudyPath.user_id == user_id)
            .order_by(StudyPath.created_at.desc())
            .limit(1)
        )
        path = result.scalar_one_or_none()
        if path:
            await redis.set(
                self._cache_key(user_id), json.dumps(self._serialize(path))
            )
        return path

    async def update_path_config(
        self, path_id: UUID, config: dict
    ) -> StudyPath:
        """Update study path configuration and refresh cache."""
        path = await self.db.get(StudyPath, path_id)
        if not path:
            raise ValueError("Study path not found")

        path.config = config
        path.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(path)

        redis = await self._get_redis()
        await redis.set(
            self._cache_key(path.user_id), json.dumps(self._serialize(path))
        )
        return path

    def _serialize(self, path: StudyPath) -> dict[str, Any]:
        return {
            "id": str(path.id),
            "user_id": path.user_id,
            "track_id": path.track_id,
            "config": path.config,
            "created_at": path.created_at.isoformat(),
            "updated_at": path.updated_at.isoformat(),
        }

    def _deserialize(self, data: bytes) -> StudyPath:
        obj = json.loads(data)
        return StudyPath(
            id=UUID(obj["id"]),
            user_id=obj["user_id"],
            track_id=obj["track_id"],
            config=obj.get("config", {}),
            created_at=datetime.fromisoformat(obj["created_at"]),
            updated_at=datetime.fromisoformat(obj["updated_at"]),
        )
