"""
Database configuration and session management
Created: 2025-01-30 13:49:00 PST
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine with proper connection pooling
engine = create_async_engine(
    str(settings.DATABASE_URL),
    poolclass=AsyncAdaptedQueuePool,
    pool_size=20,  # Number of connections to maintain in pool
    max_overflow=10,  # Maximum overflow connections above pool_size
    pool_timeout=10,  # Timeout for getting connection from pool
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Test connections before using
    echo=False,  # Set to True for SQL logging
    future=True,
    connect_args={
        "server_settings": {
            "jit": "off",
            "application_name": "smart-todo-backend"
        },
        "timeout": 5,  # Connection timeout
        "command_timeout": 30,  # Query timeout
    }
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
        except Exception as e:
            logger.error(f"Database session error: {e}")
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
        from app.models import user, task, workspace, activity, oauth, settings, chat  # noqa
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections
    """
    await engine.dispose()


def get_pool_status() -> dict:
    """
    Get current connection pool status
    """
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checked_in_connections,
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow()
    }