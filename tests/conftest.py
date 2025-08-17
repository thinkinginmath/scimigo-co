"""
Pytest configuration and shared fixtures for the CO test suite.
"""

import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test environment before importing app
os.environ["CO_ENVIRONMENT"] = "test"
os.environ["CO_DB_URL"] = "sqlite+aiosqlite:///:memory:"
# Set test JWT secret for testing
os.environ["CO_JWT_PUBLIC_KEY"] = "test-secret"
os.environ["CO_JWT_ALGORITHM"] = "HS256"  # Use HS256 for testing
# Disable rate limiting for tests
os.environ["CO_RATE_LIMIT_REQUESTS"] = "999999"
# Set mock URLs for external services to avoid network calls
os.environ["CO_EVAL_SERVICE_URL"] = "http://mock-eval:8080"
os.environ["CO_PROBLEM_BANK_URL"] = "http://mock-problem-bank:8080"
os.environ["CO_TUTOR_API_URL"] = "http://mock-tutor:8080"

from co.config import get_settings  # noqa: E402
from co.db.base import Base  # noqa: E402

settings = get_settings()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    # Use the test database URL from environment
    test_db_url = os.environ.get("CO_DB_URL", settings.db_url)

    engine = create_async_engine(test_db_url, echo=False, future=True)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_user_id():
    """Test user ID for authentication."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def test_jwt_token(test_user_id):
    """Create a test JWT token."""
    payload = {
        "sub": test_user_id,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }

    # Use test secret for signing
    token = jwt.encode(
        payload,
        "test-secret",  # Must match CO_JWT_PUBLIC_KEY
        algorithm="HS256",  # Must match CO_JWT_ALGORITHM
    )

    return token


@pytest.fixture
def app():
    """Create test app instance."""
    from contextlib import asynccontextmanager

    from co.config import get_settings
    from co.db.base import close_db, init_db
    from co.routes import sessions, study_tasks, submissions, tracks, tutor
    from fastapi import FastAPI

    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Initialize database connection on startup
        await init_db()
        yield
        # Close database connection on shutdown
        await close_db()

    # Create a simpler app for testing without problematic middleware
    test_app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    # Add only essential routes
    test_app.include_router(tracks.router, prefix="/v1/tracks", tags=["tracks"])
    test_app.include_router(sessions.router, prefix="/v1/sessions", tags=["sessions"])
    test_app.include_router(
        study_tasks.router, prefix="/v1/study-tasks", tags=["study-tasks"]
    )
    test_app.include_router(
        submissions.router, prefix="/v1/submissions", tags=["submissions"]
    )
    test_app.include_router(tutor.router, prefix="/v1/tutor", tags=["tutor"])

    # Health check
    @test_app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return test_app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    # Use TestClient with the app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_client(client, test_jwt_token):
    """Create an authenticated test client."""
    client.headers = {"Authorization": f"Bearer {test_jwt_token}"}
    return client


@pytest.fixture
def sample_track_data():
    """Sample track data for testing."""
    return {
        "slug": "test-track",
        "subject": "coding",
        "title": "Test Track",
        "labels": ["test", "sample"],
        "modules": [
            {
                "id": "arrays-strings",
                "title": "Arrays & Strings",
                "outcomes": ["two-pointers", "sliding-window"],
            }
        ],
    }


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "subject": "coding",
        "mode": "practice",
    }


@pytest.fixture
def sample_submission_data():
    """Sample submission data for testing."""
    return {
        "session_id": "550e8400-e29b-41d4-a716-446655440001",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "problem_id": "two-sum-variant",
        "subject": "coding",
        "language": "python",
        "status": "passed",
        "visible_passed": 3,
        "visible_total": 3,
        "hidden_passed": 8,
        "hidden_total": 10,
        "categories": [],
        "exec_ms": 120,
    }


@pytest.fixture
def mock_problem_bank_client():
    """Mock Problem Bank client to avoid external API calls."""
    mock_client = AsyncMock()
    mock_client.get_hidden_tests.return_value = [
        {"input": "[2,7,11,15], 9", "expected": "[0,1]"},
        {"input": "[3,2,4], 6", "expected": "[1,2]"},
    ]
    return mock_client


@pytest.fixture
def mock_eval_service_client():
    """Mock Evaluation Service client to avoid external API calls."""
    mock_client = AsyncMock()
    mock_client.submit_code.return_value = {
        "status": "passed",
        "visible_passed": 2,
        "visible_total": 2,
        "hidden_passed": 5,
        "hidden_total": 5,
        "categories": [],
        "exec_ms": 120,
    }
    return mock_client


@pytest.fixture
def mock_tutor_client():
    """Mock Tutor API client to avoid external API calls."""
    mock_client = AsyncMock()
    mock_client.create_tutor_session.return_value = {
        "stream_token": "mock-stream-token-123",
        "expires_in": 3600,
    }
    return mock_client


@pytest.fixture(autouse=True)
def mock_external_services(
    mock_problem_bank_client, mock_eval_service_client, mock_tutor_client
):
    """Auto-used fixture that mocks all external service clients."""
    with patch("co.clients.problem_bank.ProblemBankClient") as mock_pb_class, patch(
        "co.clients.eval_service.EvalServiceClient"
    ) as mock_eval_class, patch(
        "co.clients.tutor_api.TutorAPIClient"
    ) as mock_tutor_class, patch(
        "co.services.personalization.ProblemBankClient"
    ) as mock_pb_service, patch(
        "co.services.evaluators.coding.ProblemBankClient"
    ) as mock_pb_coding, patch(
        "co.services.evaluators.coding.EvalServiceClient"
    ) as mock_eval_coding, patch(
        "co.services.evaluators.math.ProblemBankClient"
    ) as mock_pb_math, patch(
        "co.services.evaluators.math.EvalServiceClient"
    ) as mock_eval_math, patch(
        "co.services.personalization.PersonalizationService"
    ) as mock_personalization_class, patch(
        "co.services.sessions.PersonalizationService"
    ) as mock_sessions_personalization, patch(
        "co.services.study_task.PersonalizationService"
    ) as mock_task_personalization:
        # Configure the mocked classes to return our mock instances
        mock_pb_class.return_value = mock_problem_bank_client
        mock_eval_class.return_value = mock_eval_service_client
        mock_tutor_class.return_value = mock_tutor_client
        mock_pb_service.return_value = mock_problem_bank_client
        mock_pb_coding.return_value = mock_problem_bank_client
        mock_eval_coding.return_value = mock_eval_service_client
        mock_pb_math.return_value = mock_problem_bank_client
        mock_eval_math.return_value = mock_eval_service_client

        # Add methods that PersonalizationService expects
        mock_problem_bank_client.get_problems_by_subject.return_value = [
            {"id": "two-sum-variant", "title": "Two Sum Variant", "difficulty": 40},
            {"id": "valid-parentheses", "title": "Valid Parentheses", "difficulty": 35},
        ]
        mock_problem_bank_client.get_problem.return_value = {
            "id": "two-sum-variant",
            "topics": ["hash-map"],
        }

        # Add methods that evaluators expect
        mock_problem_bank_client.get_hidden_bundle.return_value = {
            "tests": [
                {"input": "[2,7,11,15], 9", "expected": "[0,1]"},
                {"input": "[3,2,4], 6", "expected": "[1,2]"},
            ]
        }

        mock_eval_service_client.evaluate_code.return_value = {
            "status": "passed",
            "visible": {"passed": 2, "total": 2},
            "hidden": {"passed": 5, "total": 5, "categories": []},
            "exec_ms": 120,
        }

        # Mock personalization service
        mock_personalization = AsyncMock()
        mock_personalization.get_next_problem.return_value = "two-sum-variant"
        mock_personalization.update_mastery.return_value = None
        mock_personalization.add_to_review_queue.return_value = None
        mock_personalization.mark_review_result.return_value = None
        mock_personalization.get_due_reviews.return_value = []
        mock_personalization_class.return_value = mock_personalization
        mock_sessions_personalization.return_value = mock_personalization
        mock_task_personalization.return_value = mock_personalization

        yield
