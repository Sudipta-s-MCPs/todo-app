#!/usr/bin/env python3
"""
Test chat pattern matching
Created: 2025-01-02 08:00:00 PST
"""
import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.chat_service import ChatService

def test_patterns():
    """Test pattern matching for various commands."""
    service = ChatService()
    
    test_cases = [
        "Show my high priority tasks",
        "show my high priority tasks",  # lowercase
        "Create a task to review Q4 reports",
        "create a task to review Q4 reports",  # lowercase
        "What tasks are due this week?",
        "what tasks are due this week?",  # lowercase
        "show my tasks",
        "list tasks",
        "get all tasks",
        "what do i have to do?",
        "create task buy groceries",
        "add task call john",
        "new task finish report",
        "remind me to pick up dry cleaning",
        "todo: prepare presentation",
        "help",
        "commands",
        "show high priority tasks",
        "list medium priority tasks",
        "what is due today?",
        "what tasks are due tomorrow?",
        "show tasks due next week"
    ]
    
    print("Testing chat pattern matching...\n")
    
    for test_input in test_cases:
        print(f"Input: '{test_input}'")
        content_lower = test_input.lower()
        
        matched = False
        for pattern, action in service.PATTERN_COMMANDS.items():
            match = re.match(pattern, content_lower, re.IGNORECASE)
            if match:
                print(f"  ✓ Matched pattern: {pattern}")
                print(f"  → Action: {action}")
                if match.groups():
                    print(f"  → Groups: {match.groups()}")
                matched = True
                break
        
        if not matched:
            print(f"  ✗ No pattern match")
            # Check if it would be considered a natural language task
            task_keywords = [
                "need to", "have to", "should", "must", "remember",
                "don't forget", "make sure", "plan to", "want to",
                "tomorrow", "today", "next week", "by", "deadline",
                "urgent", "important", "asap", "priority"
            ]
            
            if any(keyword in content_lower for keyword in task_keywords):
                print(f"  → Would be processed as natural language task")
            else:
                # Check imperative mood
                first_word = content_lower.split()[0] if test_input.split() else ""
                imperative_verbs = [
                    "buy", "get", "call", "email", "send", "write", "read",
                    "finish", "complete", "review", "prepare", "schedule",
                    "book", "pay", "fix", "clean", "organize", "update"
                ]
                if first_word in imperative_verbs:
                    print(f"  → Would be processed as natural language task (imperative)")
                else:
                    print(f"  → Would not be recognized")
        
        print()

if __name__ == "__main__":
    test_patterns()