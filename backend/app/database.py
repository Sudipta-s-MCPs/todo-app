"""
Database configuration and session management
Created: 2025-01-30 13:49:00 PST
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.config import settings

# Create async engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    poolclass=NullPool,  # Disable connection pooling for async
    echo=False,  # Set to True for SQL logging
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered
        from app.models import user, task, workspace, activity  # noqa
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections
    """
    await engine.dispose()