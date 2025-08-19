"""Track management endpoints."""

from typing import Optional
from uuid import UUID

from co.db.base import get_db
from co.schemas.tracks import Track, TrackList
from co.services.tracks import TrackService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("", response_model=TrackList)
async def list_tracks(
    subject: Optional[str] = Query(None, regex="^(coding|math|systems)$"),
    label: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> TrackList:
    """List available tracks with optional filtering."""
    service = TrackService(db)
    tracks = await service.list_tracks(subject=subject, label=label)
    return TrackList(items=[Track.model_validate(t) for t in tracks])


@router.get("/{track_id}", response_model=Track)
async def get_track(
    track_id: str,
    db: AsyncSession = Depends(get_db),
) -> Track:
    """Get a track by ID or slug."""
    service = TrackService(db)

    # Try as UUID first, then as slug
    track = None
    try:
        track = await service.get_track_by_id(UUID(track_id))
    except ValueError:
        track = await service.get_track_by_slug(track_id)

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    return track
