"""
Initialize database tables
Created: 2025-01-30 14:48:00 PST
Updated: 2025-07-01 16:00:00 IST - Removed admin user creation (now using LDAP/ADMIN_USERS)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import init_db


async def main():
    """Initialize database tables"""
    print("Initializing database...")
    
    # Initialize database tables
    await init_db()
    print("Database tables created successfully")


if __name__ == "__main__":
    asyncio.run(main())