import pytest
from co.auth import get_current_user
from co.middleware import AuthMiddleware
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient


@pytest.fixture
def auth_app():
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/state")
    async def read_state(request: Request):
        return {"user_id": getattr(request.state, "user_id", None)}

    @app.get("/me")
    async def read_me(user_id=Depends(get_current_user)):
        return {"user_id": str(user_id)}

    return app


def test_auth_middleware_sets_user_id(auth_app, test_jwt_token, test_user_id):
    client = TestClient(auth_app)
    response = client.get(
        "/state", headers={"Authorization": f"Bearer {test_jwt_token}"}
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == test_user_id

    # Ensure dependency uses middleware value
    me_resp = client.get("/me", headers={"Authorization": f"Bearer {test_jwt_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["user_id"] == test_user_id


def test_auth_middleware_invalid_token(auth_app):
    client = TestClient(auth_app)
    response = client.get("/state", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert "detail" in response.json()
