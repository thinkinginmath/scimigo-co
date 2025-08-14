from co.db.models import Track


def test_track_creation() -> None:
    track = Track(
        slug="test-track",
        subject="coding",
        title="Test Track",
        labels=["test"],
        modules=[],
    )
    assert track.slug == "test-track"
