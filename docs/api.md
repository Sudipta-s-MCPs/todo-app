# Smart-ToDo API Documentation

**Created**: 2025-01-30 14:55:00 PST  
**Last Modified**: 2025-01-30 14:55:00 PST

## Overview

The Smart-ToDo API is a RESTful API built with FastAPI that provides comprehensive task management functionality with multi-device support, AI integration via MCP, and advanced features like duplicate detection.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

The API supports multiple authentication methods:

### JWT Authentication

Use for web and mobile applications.

```bash
# Login
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=yourpassword
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Use the access token in subsequent requests:
```bash
Authorization: Bearer eyJ...
```

### API Key Authentication

Use for server-to-server communication and MCP agents.

```bash
# Create API Key
POST /auth/api-keys
Authorization: Bearer {access_token}

{
  "name": "My API Key",
  "permissions": ["tasks:read", "tasks:write"],
  "expires_days": 30
}
```

Use the API key in requests:
```bash
X-API-Key: sk_todo_...
```

## Core Endpoints

### Authentication

#### Register User
```
POST /auth/register
```

#### Login
```
POST /auth/login
```

#### Refresh Token
```
POST /auth/refresh
```

#### Get Current User
```
GET /auth/me
```

#### Manage API Keys
```
GET    /auth/api-keys
POST   /auth/api-keys
DELETE /auth/api-keys/{key_id}
```

#### MCP Agent Management
```
POST /auth/mcp/register
GET  /auth/mcp/agents
POST /auth/mcp/heartbeat
```

### Workspaces

#### List Workspaces
```
GET /workspaces
```

#### Create Workspace
```
POST /workspaces
```

#### Get Workspace
```
GET /workspaces/{workspace_id}
```

#### Update Workspace
```
PUT /workspaces/{workspace_id}
```

#### Delete Workspace
```
DELETE /workspaces/{workspace_id}
```

#### Workspace Members
```
GET    /workspaces/{workspace_id}/members
POST   /workspaces/{workspace_id}/members
```

### Lists

#### Get Lists in Workspace
```
GET /workspaces/{workspace_id}/lists
```

#### Create List
```
POST /workspaces/{workspace_id}/lists
```

### Tasks

#### Create Task
```
POST /lists/{list_id}/tasks
```

Request:
```json
{
  "title": "Task title",
  "description": "Task description",
  "priority": "medium",
  "due_date": "2025-02-01T10:00:00Z",
  "assigned_to": ["user-id-1", "user-id-2"]
}
```

#### Get Task
```
GET /tasks/{task_id}
```

#### Update Task
```
PUT /tasks/{task_id}
```

#### Delete Task
```
DELETE /tasks/{task_id}
```

#### Search Tasks
```
POST /tasks/search
```

Request:
```json
{
  "query": "search term",
  "status": ["todo", "in_progress"],
  "priority": ["high", "urgent"],
  "limit": 50,
  "offset": 0
}
```

#### Check Duplicates
```
POST /tasks/{task_id}/duplicate-check
```

#### Task Comments
```
GET  /tasks/{task_id}/comments
POST /tasks/{task_id}/comments
```

## Duplicate Detection

When creating or updating tasks, the API automatically checks for duplicates based on title and description similarity. If duplicates are found, the API returns a 409 Conflict response:

```json
{
  "detail": "Potential duplicate tasks found",
  "duplicates": [
    {
      "id": "task-id",
      "title": "Similar task",
      "status": "todo"
    }
  ],
  "similarity_scores": {
    "task-id": {
      "title_similarity": 0.95,
      "description_similarity": 0.80,
      "combined_similarity": 0.88
    }
  }
}
```

To force creation/update despite duplicates:
```
POST /lists/{list_id}/tasks?force_create=true
PUT  /tasks/{task_id}?force_update=true
```

## Error Handling

The API uses standard HTTP status codes:

- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 409: Conflict (duplicates)
- 422: Validation Error
- 500: Internal Server Error

Error response format:
```json
{
  "detail": "Error message"
}
```

## Rate Limiting

- Default: 1000 requests/hour per user
- API Keys: Configurable (default 1000/hour)
- MCP Agents: 10000 requests/hour

## WebSocket Support

Real-time updates are available via WebSocket at:
```
ws://localhost:8000/ws?token=<jwt_token>&device_id=<device_id>
```

### Connection

Connect with JWT token and device ID:
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws?token=${accessToken}&device_id=${deviceId}`);
```

### Message Types

#### Client to Server

1. **Subscribe to Workspace**
```json
{
  "type": "subscribe",
  "workspace_id": "workspace-uuid"
}
```

2. **Unsubscribe from Workspace**
```json
{
  "type": "unsubscribe", 
  "workspace_id": "workspace-uuid"
}
```

3. **Typing Indicator**
```json
{
  "type": "typing",
  "data": {
    "workspace_id": "workspace-uuid",
    "list_id": "list-uuid",
    "task_id": "task-uuid",
    "is_typing": true
  }
}
```

4. **Presence Update**
```json
{
  "type": "presence",
  "status": "online" // online, away, offline
}
```

5. **Ping**
```json
{
  "type": "ping"
}
```

#### Server to Client Events

1. **Task Created**
```json
{
  "type": "task.created",
  "timestamp": "2025-01-30T23:00:00Z",
  "data": {
    "task": {
      "id": "task-uuid",
      "title": "New Task",
      "list_id": "list-uuid",
      "created_by": "user-uuid"
    }
  },
  "workspace_id": "workspace-uuid"
}
```

2. **Task Updated**
```json
{
  "type": "task.updated",
  "timestamp": "2025-01-30T23:00:00Z",
  "data": {
    "task_id": "task-uuid",
    "changes": {
      "title": {"old": "Old Title", "new": "New Title"},
      "status": {"old": "todo", "new": "in_progress"}
    },
    "updated_by": "user-uuid"
  },
  "workspace_id": "workspace-uuid"
}
```

3. **User Presence Changed**
```json
{
  "type": "user.presence_changed",
  "timestamp": "2025-01-30T23:00:00Z",
  "data": {
    "user_id": "user-uuid",
    "status": "online",
    "last_seen": "2025-01-30T23:00:00Z"
  }
}
```

### Example WebSocket Client

```python
import asyncio
import websockets
import json

async def listen_to_updates(token, device_id):
    uri = f"ws://localhost:8000/ws?token={token}&device_id={device_id}"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to workspace
        await websocket.send(json.dumps({
            "type": "subscribe",
            "workspace_id": "your-workspace-id"
        }))
        
        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['type']}")
            
            # Handle different event types
            if data['type'] == 'task.created':
                print(f"New task: {data['data']['task']['title']}")
            elif data['type'] == 'task.updated':
                print(f"Task updated: {data['data']['changes']}")
```