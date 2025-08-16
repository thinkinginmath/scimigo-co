"""Track management service."""

from typing import List, Optional
from uuid import UUID

from co.db.models import Track as TrackModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TrackService:
    """Service for managing tracks and curricula."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tracks(
        self,
        subject: Optional[str] = None,
        label: Optional[str] = None,
    ) -> List[TrackModel]:
        """List tracks with optional filtering."""
        query = select(TrackModel)

        if subject:
            query = query.where(TrackModel.subject == subject)

        if label:
            # Use JSONB contains for label filtering
            query = query.where(TrackModel.labels.contains([label]))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_track_by_id(self, track_id: UUID) -> Optional[TrackModel]:
        """Get track by ID."""
        result = await self.db.execute(
            select(TrackModel).where(TrackModel.id == track_id)
        )
        return result.scalar_one_or_none()

    async def get_track_by_slug(self, slug: str) -> Optional[TrackModel]:
        """Get track by slug."""
        result = await self.db.execute(
            select(TrackModel).where(TrackModel.slug == slug)
        )
        return result.scalar_one_or_none()
