from fastapi.testclient import TestClient


def test_meta_track_evaluation(auth_client: TestClient, mock_problem_bank_client):
    """Submitting a Meta track problem should return pillar scores."""

    mock_problem_bank_client.get_problem.return_value = {
        "id": "two-sum-variant",
        "labels": ["company:meta"],
    }

    session_res = auth_client.post(
        "/v1/sessions", json={"subject": "coding", "mode": "practice"}
    )
    assert session_res.status_code in [200, 201]
    session_id = session_res.json()["id"]

    submission_data = {
        "session_id": session_id,
        "problem_id": "two-sum-variant",
        "subject": "coding",
        "payload": {
            "language": "python",
            "code": (
                "def two_sum(nums, target):\n"
                "    for i in range(len(nums)):\n"
                "        for j in range(i+1, len(nums)):\n"
                "            if nums[i] + nums[j] == target:\n"
                "                return [i, j]\n"
                "    return []"
            ),
        },
    }

    resp = auth_client.post("/v1/submissions", json=submission_data)
    assert resp.status_code in [200, 201]
    data = resp.json()

    assert "pillar_scores" in data
    expected_pillars = [
        "problem_understanding",
        "algorithmic_correctness",
        "complexity_analysis",
        "code_quality",
        "communication",
    ]
    assert all(p in data["pillar_scores"] for p in expected_pillars)
    assert "feedback" in data
    assert "algorithmic_correctness" in data["feedback"]
