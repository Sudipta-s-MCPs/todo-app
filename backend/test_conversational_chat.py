#!/usr/bin/env python3
"""
Test conversational chat improvements
Created: 2025-07-03 13:30:00 PST
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.chat_service import chat_service
from app.config import settings
from app.services.dynamic_settings import dynamic_settings

# Test messages to verify conversational flow
test_conversations = [
    # Test 1: Greeting
    ["Hi", "What can you do?", "I need to buy groceries"],
    
    # Test 2: Direct task creation variations
    ["create a task", "Fix the login bug", "show my tasks"],
    
    # Test 3: Natural language
    ["Hello!", "I have to finish the report by tomorrow", "What tasks do I have?"],
    
    # Test 4: Multi-turn conversation
    ["Hey there", "How many tasks do I have?", "Add a task to call mom", "Thanks!"]
]

async def test_chat_conversation(messages: list, user_id: str = "02570849-d54e-4b46-9505-8e715e7c6acc"):
    """Test a conversation flow"""
    # Create database connection
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print(f"\n{'='*60}")
    print("CONVERSATION TEST")
    print(f"{'='*60}\n")
    
    conversation_id = None
    
    async with async_session() as db:
        # Ensure dynamic settings are loaded
        if not dynamic_settings._loaded:
            await dynamic_settings.refresh()
            
        for message in messages:
            print(f"👤 User: {message}")
            
            try:
                # Process message
                result = await chat_service.process_message(
                    content=message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    db=db
                )
                
                # Update conversation ID
                if not conversation_id and result.get("conversationId"):
                    conversation_id = result["conversationId"]
                
                # Display response
                response = result.get("message", {}).get("content", "No response")
                provider = result.get("provider", "unknown")
                used_ai = result.get("usedAI", False)
                
                print(f"🤖 Assistant [{provider}, AI: {used_ai}]: {response}")
                
                # Show any created tasks
                if result.get("tasks"):
                    print(f"   📋 Tasks: {[t['title'] for t in result['tasks']]}")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)}")
            
            print()
            
            # Small delay between messages
            await asyncio.sleep(0.5)
    
    await engine.dispose()

async def main():
    """Run all conversation tests"""
    print("Testing Conversational Chat Improvements")
    print("="*60)
    
    # Test each conversation
    for i, conversation in enumerate(test_conversations, 1):
        print(f"\n\n🧪 Test Conversation {i}")
        # Use the existing user for testing
        await test_chat_conversation(conversation)
        
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())