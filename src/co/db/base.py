"""Database connection and session management."""

from typing import Any, AsyncGenerator, Dict, Optional

from co.config import get_settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Global engine and sessionmaker
engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db() -> None:
    """Initialize database connection."""
    global engine, AsyncSessionLocal

    settings = get_settings()

    engine_args: Dict[str, Any] = {
        "pool_pre_ping": True,
        "echo": settings.debug,
    }

    # SQLite (used in tests) doesn't support pool_size/max_overflow
    if not settings.db_url.startswith("sqlite"):
        engine_args["pool_size"] = settings.db_pool_size
        engine_args["max_overflow"] = settings.db_max_overflow

    engine = create_async_engine(
        settings.db_url,
        **engine_args,
    )

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # For in-memory SQLite used in tests, create tables automatically
    if settings.db_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connection."""
    global engine

    if engine is not None:
        await engine.dispose()
        engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    if AsyncSessionLocal is None:
        await init_db()

    assert AsyncSessionLocal is not None

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
