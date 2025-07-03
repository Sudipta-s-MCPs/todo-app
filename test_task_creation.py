#!/usr/bin/env python3
"""
Test task creation through chat service
Created: 2025-07-03 12:10:00 PST
"""

import asyncio
import re
from app.services.chat_service import ChatService

# Test patterns
test_messages = [
    "create task buy groceries",
    "add task review reports",
    "new task call john",
    "remind me to pick up dry cleaning",
    "todo: finish the presentation",
    "task: update documentation",
    "I need to fix the bug in login page",  # Should not match pattern
]

async def test_pattern_matching():
    """Test pattern matching for task creation"""
    chat_service = ChatService()
    
    print("Testing task creation patterns:\n")
    
    for message in test_messages:
        print(f"Message: '{message}'")
        
        # Try pattern matching
        matched = False
        for pattern, action in chat_service.PATTERN_COMMANDS.items():
            match = re.match(pattern, message.lower(), re.IGNORECASE)
            if match and action == "create_task":
                matched = True
                groups = match.groups()
                print(f"  ✓ Matched pattern: {pattern}")
                print(f"  Groups: {groups}")
                
                # Extract task title based on pattern
                if len(groups) == 3:
                    task_title = match.group(3)
                else:
                    task_title = match.group(1)
                    
                print(f"  Task title: '{task_title}'")
                break
        
        if not matched:
            print(f"  ✗ No pattern match - would use AI processing")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_pattern_matching())