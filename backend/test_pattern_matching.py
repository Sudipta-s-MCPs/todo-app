#!/usr/bin/env python3
"""
Test pattern matching quickly
Created: 2025-07-03 13:45:00 PST
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.chat_service import chat_service
from app.config import settings
from app.services.dynamic_settings import dynamic_settings

# Simple test messages
test_messages = [
    "hi",
    "create a task",
    "show my tasks",
    "help"
]

async def quick_test():
    """Quick test of pattern matching"""
    # Create database connection
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    user_id = "02570849-d54e-4b46-9505-8e715e7c6acc"  # Existing user
    
    print("Testing Pattern Matching\n" + "="*50)
    
    async with async_session() as db:
        # Ensure dynamic settings are loaded
        if not dynamic_settings._loaded:
            await dynamic_settings.refresh()
            
        for message in test_messages:
            print(f"\n👤 User: {message}")
            
            try:
                # Process message with short timeout
                result = await asyncio.wait_for(
                    chat_service.process_message(
                        content=message,
                        user_id=user_id,
                        conversation_id=None,
                        db=db
                    ),
                    timeout=10.0  # 10 second timeout
                )
                
                # Display response
                response = result.get("message", {}).get("content", "No response")
                provider = result.get("provider", "unknown")
                used_ai = result.get("usedAI", False)
                
                print(f"🤖 Assistant [{provider}, AI: {used_ai}]:")
                print(f"   {response[:200]}..." if len(response) > 200 else f"   {response}")
                
            except asyncio.TimeoutError:
                print(f"❌ Timeout after 10 seconds")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    await engine.dispose()
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(quick_test())