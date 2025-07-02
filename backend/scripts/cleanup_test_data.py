#!/usr/bin/env python3
"""
Clean up test data from database
Created: 2025-01-02 21:25:00 PST
Updated: 2025-07-02 11:00:00 PST - Keep only Sudipta user and settings
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
    """Clean up all test data except settings and Sudipta user"""
    # Create database connection
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://sd_todo_app_user:AAqLX5r0lzm53hgQu48XIClw@192.168.11.100:15432/sd_todo_app_db")
    
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        try:
            print("Starting database cleanup...")
            
            # First, find Sudipta's user ID
            print("Finding Sudipta user...")
            result = await db.execute(
                text("SELECT id, email, name FROM users WHERE LOWER(name) = 'sudipta' OR LOWER(email) LIKE '%sudipta%'")
            )
            sudipta_user = result.first()
            
            if not sudipta_user:
                print("WARNING: Sudipta user not found! Aborting cleanup.")
                return
            
            sudipta_id = sudipta_user.id
            print(f"Found Sudipta: {sudipta_user.email} (ID: {sudipta_id})")
            
            # Delete data for all users except Sudipta
            tables_with_user_id = [
                ("activity_logs", "user_id"),
                ("task_attachments", "uploaded_by"),
                ("task_assignments", "user_id"),
                ("tasks", "created_by"),
                ("workspace_members", "user_id"),
                ("workspaces", "owner_id"),
                ("api_keys", "user_id"),
                ("mcp_agents", "user_id"),
                ("user_sessions", "user_id"),
                ("user_devices", "user_id")
            ]
            
            # Tables without direct user reference - delete all
            tables_to_clear_completely = [
                "task_comments",  # No user_id column
                "lists"          # No direct user reference
            ]
            
            # Delete data for non-Sudipta users
            for table, user_column in tables_with_user_id:
                print(f"Deleting non-Sudipta data from {table}...")
                try:
                    result = await db.execute(
                        text(f"DELETE FROM {table} WHERE {user_column} != :user_id"),
                        {"user_id": sudipta_id}
                    )
                    await db.commit()  # Commit after each successful deletion
                    print(f"  Deleted {result.rowcount} rows")
                except Exception as e:
                    print(f"  Warning: Could not clean {table}: {e}")
                    await db.rollback()  # Rollback on error
            
            # Clear tables without user references completely
            for table in tables_to_clear_completely:
                print(f"Clearing all data from {table}...")
                try:
                    result = await db.execute(text(f"DELETE FROM {table}"))
                    await db.commit()
                    print(f"  Deleted {result.rowcount} rows")
                except Exception as e:
                    print(f"  Warning: Could not clear {table}: {e}")
                    await db.rollback()
            
            # Delete all users except Sudipta
            print("Deleting all users except Sudipta...")
            try:
                result = await db.execute(
                    text("DELETE FROM users WHERE id != :user_id"),
                    {"user_id": sudipta_id}
                )
                await db.commit()
                print(f"  Deleted {result.rowcount} user(s)")
            except Exception as e:
                print(f"  Warning: Could not delete users: {e}")
                await db.rollback()
            
            # Clean up orphaned data (tasks without valid workspaces, etc.)
            print("Cleaning up orphaned data...")
            
            orphan_cleanup_queries = [
                ("task_attachments (orphaned)", """
                    DELETE FROM task_attachments WHERE task_id IN (
                        SELECT id FROM tasks WHERE list_id NOT IN (SELECT id FROM lists)
                    )
                """),
                ("task_comments (orphaned)", """
                    DELETE FROM task_comments WHERE task_id IN (
                        SELECT id FROM tasks WHERE list_id NOT IN (SELECT id FROM lists)
                    )
                """),
                ("task_assignments (orphaned)", """
                    DELETE FROM task_assignments WHERE task_id IN (
                        SELECT id FROM tasks WHERE list_id NOT IN (SELECT id FROM lists)
                    )
                """),
                ("tasks (orphaned)", "DELETE FROM tasks WHERE list_id NOT IN (SELECT id FROM lists)"),
                ("lists (orphaned)", "DELETE FROM lists WHERE workspace_id NOT IN (SELECT id FROM workspaces)"),
                ("workspace_members (orphaned)", "DELETE FROM workspace_members WHERE workspace_id NOT IN (SELECT id FROM workspaces)")
            ]
            
            for name, query in orphan_cleanup_queries:
                try:
                    result = await db.execute(text(query))
                    await db.commit()
                    if result.rowcount > 0:
                        print(f"  Deleted {result.rowcount} {name}")
                except Exception as e:
                    print(f"  Warning: Could not clean {name}: {e}")
                    await db.rollback()
            
            # Show final status
            print("\n=== Cleanup Summary ===")
            
            # Count remaining data
            for table in ["users", "workspaces", "lists", "tasks", "system_settings"]:
                result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"{table}: {count} records")
            
            print(f"\nKept user: {sudipta_user.email} ({sudipta_user.name})")
            print("System settings: Preserved")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            await db.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_database())