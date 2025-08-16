"""Track-related schemas."""

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel


class Module(BaseModel):
    """Module within a track."""

    id: str
    title: str
    outcomes: List[str] = []


class Track(BaseModel):
    """Track/curriculum schema."""

    id: UUID
    slug: str
    subject: str
    title: str
    modules: List[Module] = []
    labels: List[str] = []
    version: str = "v1"
    created_at: datetime

    class Config:
        from_attributes = True


class TrackList(BaseModel):
    """List of tracks."""

    items: List[Track]
