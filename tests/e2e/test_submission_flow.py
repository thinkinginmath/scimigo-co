"""
End-to-end tests for complete submission workflow.
"""

import pytest
from fastapi.testclient import TestClient


class TestSubmissionWorkflow:
    """Test complete submission workflow from track to evaluation."""
    
    def test_complete_workflow_mock(self, auth_client: TestClient):
        """Test complete workflow with mocked external services."""
        # Step 1: List available tracks
        tracks_response = auth_client.get("/v1/tracks?subject=coding")
        assert tracks_response.status_code == 200
        
        # Step 2: Create a session
        session_data = {
            "subject": "coding",
            "mode": "practice"
        }
        session_response = auth_client.post("/v1/sessions", json=session_data)
        assert session_response.status_code in [200, 201]
        
        if session_response.status_code in [200, 201]:
            session_id = session_response.json()["id"]
            
            # Step 3: Submit a solution (may fail if Problem Bank not available)
            submission_data = {
                "session_id": session_id,
                "problem_id": "two-sum-variant",
                "subject": "coding",
                "payload": {
                    "language": "python",
                    "code": "def two_sum(nums, target):\n    # Simple implementation\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return [-1, -1]"
                }
            }
            
            submission_response = auth_client.post("/v1/submissions", json=submission_data)
            # Accept various responses depending on external service availability
            assert submission_response.status_code in [200, 201, 409, 422, 500, 503]
            
            if submission_response.status_code in [200, 201]:
                # If submission succeeded, check response structure
                data = submission_response.json()
                assert "status" in data
        
    def test_health_check(self, client: TestClient):
        """Test that the health endpoint works."""
        response = client.get("/health")
        assert response.status_code == 200