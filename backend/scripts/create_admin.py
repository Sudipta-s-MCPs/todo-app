#!/usr/bin/env python3
"""
Create initial admin user
Created: 2025-07-02 16:30:00 PST
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

# Add parent directory to path
sys.path.append('/app')

from app.database import AsyncSessionLocal
from app.models.user import User
from app.utils.security import get_password_hash

async def create_admin():
    """Create initial admin user"""
    async with AsyncSessionLocal() as session:
        # Check if admin exists
        result = await session.execute(
            select(User).where(User.email == "admin@smarttodo.local")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin = User(
            email="admin@smarttodo.local",
            name="Admin",
            password_hash=get_password_hash("admin123"),
            is_active=True,
            is_admin=True,
            is_verified=True,
            approval_status="approved",
            approved_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(admin)
        await session.commit()
        
        print("Admin user created successfully!")
        print("Email: admin@smarttodo.local")
        print("Password: admin123")
        print("\nPLEASE CHANGE THE PASSWORD AFTER FIRST LOGIN!")

if __name__ == "__main__":
    asyncio.run(create_admin())