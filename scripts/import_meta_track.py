import asyncio
from sqlalchemy import select

from co.clients.problem_bank import ProblemBankClient
from co.db import base
from co.db.models import Track

TRACK_SLUG = "coding-interview-meta"


async def import_meta_track() -> Track:
    """Import Meta coding interview track from Problem Bank into local DB."""
    if base.engine is None:
        await base.init_db()
    client = ProblemBankClient()
    track_data = await client.get_track(TRACK_SLUG)

    async with base.AsyncSessionLocal() as session:
        # Check if track already exists
        existing = await session.execute(select(Track).where(Track.slug == track_data["slug"]))
        track = existing.scalar_one_or_none()
        if track:
            return track

        track = Track(
            slug=track_data["slug"],
            subject=track_data["subject"],
            title=track_data["title"],
            labels=track_data.get("labels", []),
            modules=track_data.get("modules", []),
            version=track_data.get("version", "v1"),
        )
        session.add(track)
        await session.commit()
        await session.refresh(track)
        return track


def main() -> None:
    asyncio.run(import_meta_track())


if __name__ == "__main__":
    main()
