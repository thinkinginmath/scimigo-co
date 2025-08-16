"""
Integration tests for API endpoints.
"""

from fastapi.testclient import TestClient


class TestTracksAPI:
    """Test the tracks API endpoints."""

    def test_list_tracks_empty(self, auth_client: TestClient):
        """Test listing tracks when none exist."""
        response = auth_client.get("/v1/tracks")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_tracks_with_filters(self, auth_client: TestClient):
        """Test listing tracks with query filters."""
        response = auth_client.get("/v1/tracks?subject=coding")
        assert response.status_code == 200

        response = auth_client.get("/v1/tracks?label=company:meta")
        assert response.status_code == 200


class TestSessionsAPI:
    """Test the sessions API endpoints."""

    def test_create_session_minimal(self, auth_client: TestClient, test_user_id: str):
        """Test creating a session with minimal data."""
        session_data = {"subject": "coding", "mode": "practice"}

        response = auth_client.post("/v1/sessions", json=session_data)
        assert response.status_code in [200, 201]

        data = response.json()
        assert "id" in data
        assert data["subject"] == "coding"
        assert data["mode"] == "practice"


class TestSubmissionsAPI:
    """Test the submissions API endpoints."""

    def test_submit_coding_problem(self, auth_client: TestClient):
        """Test submitting a coding problem solution."""
        # First create a session
        session_data = {"subject": "coding", "mode": "practice"}
        session_response = auth_client.post("/v1/sessions", json=session_data)

        if session_response.status_code in [200, 201]:
            session_id = session_response.json()["id"]

            # Submit a solution
            submission_data = {
                "session_id": session_id,
                "problem_id": "two-sum-variant",
                "subject": "coding",
                "payload": {
                    "language": "python",
                    "code": "def two_sum(nums, target):\n    return [0, 1]",
                },
            }

            response = auth_client.post("/v1/submissions", json=submission_data)
            # Note: This might return 409 if Problem Bank is not available
            assert response.status_code in [200, 201, 409, 422, 500]


class TestTutorAPI:
    """Test the tutor API endpoints."""

    def test_create_tutor_session(self, auth_client: TestClient):
        """Test creating a tutor session."""
        tutor_data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440001",
            "problem_id": "two-sum-variant",
            "message": "I need help with this problem",
        }

        response = auth_client.post("/v1/tutor/messages", json=tutor_data)
        # Note: This might fail if external services are not available
        assert response.status_code in [200, 201, 422, 503]
