"""FastAPI application factory and server configuration."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from co.config import get_settings
from co.db.base import close_db, init_db
from co.middleware import AuthMiddleware, RateLimitMiddleware, RequestIDMiddleware
from co.routes import sessions, submissions, study_tasks, tracks, tutor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    await init_db()

    yield

    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Routes
    app.include_router(tracks.router, prefix="/v1/tracks", tags=["tracks"])
    app.include_router(sessions.router, prefix="/v1/sessions", tags=["sessions"])
    app.include_router(
        study_tasks.router, prefix="/v1/study-tasks", tags=["study-tasks"]
    )
    app.include_router(
        submissions.router, prefix="/v1/submissions", tags=["submissions"]
    )
    app.include_router(tutor.router, prefix="/v1/tutor", tags=["tutor"])

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "curriculum-orchestrator"}

    # Root redirect
    @app.get("/")
    async def root():
        return JSONResponse(
            content={
                "service": "Scimigo Curriculum Orchestrator",
                "version": "0.1.0",
                "docs": "/docs" if settings.debug else None,
            }
        )

    return app


app = create_app()
