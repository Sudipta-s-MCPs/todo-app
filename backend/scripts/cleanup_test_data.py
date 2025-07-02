#!/usr/bin/env python3
"""
Clean up test data from database
Created: 2025-01-02 21:25:00 PST
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


async def cleanup_database():
    """Clean up all test data except users"""
    # Create database connection
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://sd_todo_app_user:AAqLX5r0lzm53hgQu48XIClw@postgres:5432/sd_todo_app_db")
    
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        try:
            print("Starting database cleanup...")
            
            # Delete in correct order to respect foreign key constraints
            tables_in_order = [
                # Activity logs first (references sessions and devices)
                "activity_logs",
                
                # Task related
                "task_attachments",
                "task_comments", 
                "task_assignments",
                "task_modifications",  # This references tasks
                "tasks",
                
                # List related
                "lists",
                
                # Workspace related
                "workspace_members",
                "workspaces",
                
                # Auth related
                "api_keys",
                "mcp_agents",
                "user_sessions",
                "user_devices"
            ]
            
            for table in tables_in_order:
                print(f"Deleting from {table}...")
                try:
                    result = await db.execute(text(f"DELETE FROM {table}"))
                    print(f"  Deleted {result.rowcount} rows")
                except Exception as e:
                    print(f"  Warning: Could not clean {table}: {e}")
            
            # Commit all deletions
            await db.commit()
            
            # Count remaining users
            result = await db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            
            print(f"\nCleanup complete! Kept {user_count} user(s)")
            
            # Show user details
            result = await db.execute(text("SELECT email, name FROM users"))
            for row in result:
                print(f"  - {row.email} ({row.name})")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            await db.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_database())