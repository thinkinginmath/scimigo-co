import json
from pathlib import Path

import pytest
from co.db import base
from co.db.models import Track
from sqlalchemy import select

import scripts.import_meta_track as meta_script


@pytest.mark.asyncio
async def test_import_meta_track(mock_problem_bank_client, monkeypatch):
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "sample_problems.json"
    )
    data = json.loads(fixture_path.read_text())
    track_data = data["tracks"][0]

    # Configure mock problem bank to return our track data
    mock_problem_bank_client.get_track.return_value = track_data
    monkeypatch.setattr(
        meta_script, "ProblemBankClient", lambda: mock_problem_bank_client
    )

    # Initialize database and create tables
    if base.engine is None:
        await base.init_db()
    async with base.engine.begin() as conn:
        await conn.run_sync(base.Base.metadata.create_all)

    track = await meta_script.import_meta_track()

    assert track.slug == track_data["slug"]
    assert track.title == track_data["title"]

    # Verify persisted in database
    async with base.AsyncSessionLocal() as session:
        result = await session.execute(
            select(Track).where(Track.slug == track_data["slug"])
        )
        stored = result.scalar_one_or_none()
        assert stored is not None
        assert stored.modules[0]["id"] == track_data["modules"][0]["id"]
