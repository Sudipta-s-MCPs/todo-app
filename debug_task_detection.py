#!/usr/bin/env python3
"""Debug script to test task detection logic."""

def debug_looks_like_task_creation(content: str) -> bool:
    """Debug version of _looks_like_task_creation with detailed logging."""
    print(f"\n=== Debugging: '{content}' ===")
    
    # Keywords that suggest task creation
    task_keywords = [
        "need to", "have to", "should", "must", "remember",
        "don't forget", "make sure", "plan to", "want to",
        "tomorrow", "today", "next week", "by", "deadline",
        "urgent", "important", "asap", "priority"
    ]
    
    content_lower = content.lower()
    print(f"Content (lowercase): '{content_lower}'")
    
    # Check for task-like keywords
    found_keywords = [kw for kw in task_keywords if kw in content_lower]
    print(f"Found keywords: {found_keywords}")
    
    if found_keywords:
        print("✅ MATCHED by keywords!")
        return True
    
    # Check for imperative mood (starts with verb)
    words = content_lower.split()
    first_word = words[0] if words else ""
    print(f"First word: '{first_word}'")
    
    imperative_verbs = [
        "buy", "get", "call", "email", "send", "write", "read",
        "finish", "complete", "review", "prepare", "schedule",
        "book", "pay", "fix", "clean", "organize", "update"
    ]
    
    print(f"Imperative verbs: {imperative_verbs}")
    print(f"First word in imperative verbs? {first_word in imperative_verbs}")
    
    if first_word in imperative_verbs:
        print("✅ MATCHED by imperative verb!")
        return True
    
    print("❌ NO MATCH")
    return False

# Test cases
test_cases = [
    "Schedule meeting with team tomorrow at 3pm",
    "Create a task to review Q4 reports", 
    "Show my high priority tasks",
    "I need to call John tomorrow",
    "Buy groceries",
    "Meeting with client",
    "Appointment at 2pm",
    "Plan project review"
]

print("Task Detection Debug Results:")
print("=" * 50)

for test in test_cases:
    result = debug_looks_like_task_creation(test)
    print(f"Result: {result}")
    print("-" * 30)