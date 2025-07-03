# Chat Pattern Matching Documentation

**Created**: 2025-07-03 07:35:00 PST  
**Last Updated**: 2025-07-03 07:35:00 PST

## Overview

The Smart-ToDo chat service uses a hybrid approach combining AI processing with pattern matching for reliable task management. This document outlines the pattern matching capabilities for English language inputs.

## Task Creation Patterns

The system recognizes various natural ways to create tasks:

### Direct Commands
- `create task [title]` - Creates a task with the given title
- `add task [title]` - Adds a new task
- `new task [title]` - Creates a new task
- `create a task` - Prompts for task details

### Natural Language
- `remind me to [action]` - Creates a reminder task
- `todo: [task]` - Quick task creation
- `task: [task]` - Alternative quick creation
- `I need to [action]` - Natural expression of needs
- `I have to [action]` - Express obligations
- `I must [action]` - Express urgent needs
- `don't forget to [action]` - Create reminder tasks
- `remember to [action]` - Alternative reminder
- `need to [action]` - Simple need expression
- `have to [action]` - Simple obligation

### Examples
- "I need to buy groceries"
- "remind me to call the dentist"
- "todo: finish the presentation"
- "don't forget to submit timesheet"

## Task Completion Patterns

The system supports flexible ways to mark tasks as completed:

### Mark-based Commands
- `mark [task] as done` - Classic completion command
- `mark the [task] as done` - With article
- `mark [task] task as done` - With "task" word
- `mark the [task] task as done` - Full verbose form
- `mark [task] as complete` - Alternative completion word
- `mark [task] as finished` - Another alternative

### Action-first Commands
- `complete [task]` - Direct completion
- `complete the [task]` - With article
- `complete the [task] task` - With "task" word
- `finish [task]` - Alternative action
- `done with [task]` - Casual completion

### State-based Expressions
- `[task] is done` - State declaration
- `[task] task is done` - With "task" word
- `[task] is complete` - Alternative state
- `[task] is finished` - Another alternative

### Personal Expressions
- `I've done [task]` - Personal accomplishment
- `I've finished [task]` - Alternative expression
- `I've completed [task]` - Another alternative
- `I'm done with [task]` - Current state
- `just finished [task]` - Recent completion
- `completed the [task] task` - Past tense

### Checklist-style
- `check off [task]` - Checklist metaphor
- `tick off [task]` - British variant
- `tick [task]` - Shortened form

### Examples
- "mark the Fix profile page task as done" ✅
- "I've finished the bug fix"
- "check off buy groceries"
- "presentation is complete"

## Task Listing Patterns

### Basic Listing
- `show my tasks` - Display all active tasks
- `list tasks` - Alternative command
- `get tasks` - Another alternative
- `what do I have to do?` - Natural query

### Priority-based Filtering
- `show high priority tasks` - Filter by high priority
- `list medium priority tasks` - Filter by medium priority
- `show low priority tasks` - Filter by low priority

### Time-based Filtering
- `what's due today?` - Tasks due today
- `show tasks due tomorrow` - Tasks due tomorrow
- `list tasks due this week` - Weekly view
- `what tasks are due next week?` - Future view

### Workspace-specific
- `show tasks in [workspace]` - Tasks in specific workspace
- `list tasks in [workspace]` - Alternative command

## Other Patterns

### Greetings
- `hi`, `hello`, `hey` - Simple greetings
- `good morning`, `good afternoon`, `good evening` - Time-based
- `how are you?` - Conversational greeting
- `what's up?` - Casual greeting

### Help & Information
- `help` - Show help information
- `what can you do?` - Capabilities query
- `show me what you can do` - Alternative query
- `what are your capabilities?` - Formal query

### Workspace Management
- `show my workspaces` - List all workspaces
- `list workspaces` - Alternative command
- `create workspace [name]` - Create new workspace

## Implementation Notes

1. **Case Insensitive**: All patterns are matched case-insensitively
2. **Flexible Spacing**: Extra spaces are normalized
3. **Optional Words**: Articles (the, a) and words like "task" are often optional
4. **Partial Matching**: For task names, both exact and partial matches are supported
5. **Disambiguation**: When multiple tasks match, the system asks for clarification

## Future Enhancements

- Multi-lingual support (planned)
- Voice command optimization
- Context-aware pattern refinement
- Custom user patterns