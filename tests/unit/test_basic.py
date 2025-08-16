"""
Basic unit tests to verify the app setup.
"""


def test_app_creation(app):
    """Test that the app can be created."""
    assert app is not None
    assert app.title == "Scimigo Curriculum Orchestrator"


def test_health_endpoint(client):
    """Test the health endpoint without authentication."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_tracks_without_auth(client):
    """Test that tracks endpoint works without authentication."""
    response = client.get("/v1/tracks")
    # Tracks endpoint doesn't require auth based on the route definition
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_tracks_with_auth(auth_client):
    """Test tracks endpoint with authentication."""
    response = auth_client.get("/v1/tracks")
    # Should work with auth
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
