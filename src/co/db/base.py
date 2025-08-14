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
    
    engine = create_async_engine(
        settings.db_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


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