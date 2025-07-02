# MCP Integration Guide

**Created**: 2025-01-30 14:56:00 PST  
**Last Modified**: 2025-01-30 14:56:00 PST

## Overview

Smart-ToDo includes a built-in MCP (Model Context Protocol) server that allows AI assistants to interact with your tasks programmatically. This guide explains how to set up and use the MCP integration.

## Setup

### 1. Register an MCP Agent

First, register your MCP agent to get an API key:

```bash
cd backend
python mcp_server/setup_mcp.py
```

Enter your Smart-ToDo credentials when prompted. This will generate:
- API Key for authentication
- Agent ID for tracking
- Configuration instructions

### 2. Configure Environment

Set the following environment variables:

```bash
export TODO_API_KEY=sk_todo_...
export TODO_DEVICE_ID=mcp_...
export TODO_DEVICE_NAME="My AI Assistant"
export TODO_API_ENDPOINT=http://localhost:8000/api/v1
```

### 3. Run the MCP Server

```bash
cd backend
python mcp_server/server.py
```

Or use with Claude Desktop by adding to your MCP configuration:

```json
{
  "mcpServers": {
    "smart-todo": {
      "command": "python",
      "args": ["/path/to/backend/mcp_server/server.py"],
      "env": {
        "TODO_API_KEY": "your-api-key",
        "TODO_API_ENDPOINT": "http://localhost:8000/api/v1"
      }
    }
  }
}
```

## Available Tools

### Task Management

#### create_task
Create a new task with automatic duplicate detection.

```python
await create_task({
    "title": "Buy groceries",
    "description": "Get milk, eggs, and bread",
    "list_name": "Shopping",
    "priority": "high",
    "due_date": "2025-02-01T10:00:00Z"
})
```

#### list_tasks
List tasks with optional filters.

```python
await list_tasks(
    workspace_name="Personal",
    status="todo",
    limit=20
)
```

#### update_task
Update existing task properties.

```python
await update_task({
    "task_id": "task-uuid",
    "status": "in_progress",
    "priority": "urgent"
})
```

#### complete_task
Mark a task as completed.

```python
await complete_task("task-uuid")
```

#### delete_task
Delete (archive) a task.

```python
await delete_task("task-uuid")
```

#### search_tasks
Search for tasks by text query.

```python
await search_tasks("meeting notes", limit=10)
```

### List Management

#### create_list
Create a new list in a workspace.

```python
await create_list(
    name="Project Tasks",
    workspace_name="Work",
    color="#ff5722"
)
```

#### get_lists
Get all lists organized by workspace.

```python
await get_lists()
```

#### move_task
Move a task to a different list.

```python
await move_task(
    task_id="task-uuid",
    list_name="Done"
)
```

### Utility Tools

#### get_upcoming_tasks
Get tasks due in the next N days.

```python
await get_upcoming_tasks(days=7)
```

## Resources

The MCP server provides resources for passive data access:

### tasks://recent
Returns recently modified tasks.

### tasks://upcoming
Returns tasks due in the next 7 days.

## Prompts

Pre-configured prompts for common workflows:

### daily_planning_prompt
Helps organize daily tasks.

### project_breakdown_prompt
Breaks down projects into actionable tasks.

### task_review_prompt
Reviews and cleans up task lists.

## Example Usage

Here's a complete example of using the MCP server:

```python
# Create a new task
result = await create_task({
    "title": "Prepare presentation",
    "description": "Create slides for Q1 review",
    "priority": "high"
})

# If duplicates found, handle them
if result["status"] == "cancelled":
    duplicates = result["duplicates"]
    print(f"Found {len(duplicates)} similar tasks")
else:
    task_id = result["task"]["id"]
    print(f"Created task: {task_id}")

# List all high-priority tasks
tasks = await list_tasks(status="todo", limit=50)
high_priority = [t for t in tasks["tasks"] if t["priority"] in ["high", "urgent"]]

# Complete a task
await complete_task(task_id)
```

## Best Practices

1. **Handle Duplicates**: Always check the response when creating tasks
2. **Use Descriptive Names**: Help the duplicate detection by using clear task titles
3. **Batch Operations**: Use search to find multiple tasks before bulk operations
4. **Regular Heartbeats**: Keep your MCP agent active with periodic heartbeats
5. **Error Handling**: Implement retry logic for network failures

## Security

- API keys are hashed before storage
- Each MCP agent has its own permissions
- All actions are logged with full attribution
- Rate limits prevent abuse