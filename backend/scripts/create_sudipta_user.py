#!/usr/bin/env python3
"""
Create Sudipta user
Created: 2025-07-02 16:55:00 PST
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

async def create_sudipta():
    """Create Sudipta user"""
    async with AsyncSessionLocal() as session:
        # Check if user exists
        result = await session.execute(
            select(User).where(User.email == "sudipta@smarttodo.local")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Sudipta user already exists!")
            return
        
        # Create user
        user = User(
            email="sudipta@smarttodo.local",
            name="Sudipta",
            password_hash=get_password_hash("sudipta123"),
            is_active=True,
            is_admin=True,
            is_verified=True,
            approval_status="approved",
            approved_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(user)
        await session.commit()
        
        print("Sudipta user created successfully!")
        print("Email: sudipta@smarttodo.local")
        print("Password: sudipta123")
        print("\nPLEASE CHANGE THE PASSWORD AFTER FIRST LOGIN!")

if __name__ == "__main__":
    asyncio.run(create_sudipta())