#!/usr/bin/env python3
"""
Initialize system settings from environment variables
Created: 2025-01-02 07:30:00 PST
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.services.settings_service import settings_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_settings():
    """Initialize system settings"""
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Initializing system settings...")
            await settings_service.initialize_settings(db)
            logger.info("System settings initialized successfully!")
            
        except Exception as e:
            logger.error(f"Error initializing settings: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(init_settings())