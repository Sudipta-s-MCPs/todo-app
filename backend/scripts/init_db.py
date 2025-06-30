"""
Initialize database with admin user and initial data
Created: 2025-01-30 14:48:00 PST
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import init_db, get_db
from app.models.user import User
from app.models.workspace import Workspace, List, ListType
from app.utils.security import get_password_hash
from app.config import settings


async def create_admin_user(db):
    """Create the initial admin user"""
    # Check if admin already exists
    admin = await db.execute(
        select(User).where(User.email == settings.ADMIN_EMAIL)
    )
    if admin.scalar_one_or_none():
        print("Admin user already exists")
        return None
    
    # Create admin user
    admin_user = User(
        email=settings.ADMIN_EMAIL,
        name="Admin User",
        password_hash=get_password_hash(settings.ADMIN_PASSWORD),
        is_admin=True,
        is_active=True,
        is_verified=True
    )
    db.add(admin_user)
    await db.flush()
    
    print(f"Created admin user: {settings.ADMIN_EMAIL}")
    return admin_user


async def create_default_workspace(db, user):
    """Create default workspace for user"""
    # Create personal workspace
    workspace = Workspace(
        name="Personal",
        type="personal",
        owner_id=user.id
    )
    db.add(workspace)
    await db.flush()
    
    # Create default list
    default_list = List(
        workspace_id=workspace.id,
        name="Tasks",
        type=ListType.DEFAULT,
        is_default=True,
        color="#1976d2"
    )
    db.add(default_list)
    
    print(f"Created default workspace and list for {user.email}")
    return workspace


async def main():
    """Initialize database with initial data"""
    print("Initializing database...")
    
    # Initialize database tables
    await init_db()
    print("Database tables created")
    
    # Create initial data
    async for db in get_db():
        try:
            # Create admin user
            admin = await create_admin_user(db)
            
            if admin:
                # Create default workspace for admin
                await create_default_workspace(db, admin)
            
            await db.commit()
            print("Initial data created successfully")
            
        except Exception as e:
            await db.rollback()
            print(f"Error creating initial data: {e}")
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(main())