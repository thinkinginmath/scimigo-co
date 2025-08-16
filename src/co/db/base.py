"""Database connection and session management."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from co.config import get_settings

Base = declarative_base()

# Global engine and sessionmaker
engine = None
AsyncSessionLocal = None


async def init_db() -> None:
    """Initialize database connection."""
    global engine, AsyncSessionLocal
    
    settings = get_settings()
    
    engine_args = {
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
    
    if engine:
        await engine.dispose()
        engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    if not AsyncSessionLocal:
        await init_db()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()