# Claude Code Instructions: Replace FastMCP with Official MCP Library

> **⚠️ ARCHIVED DOCUMENT - MIGRATION COMPLETE**  
> This migration has been successfully completed on 2025-07-14.  
> The official MCP library is now in use at `backend/mcp_server/server_official.py`.  
> This document is preserved for historical reference only.

## 📋 Overview

This document provides step-by-step instructions for replacing the FastMCP implementation in your Smart-ToDo MCP Server with the official MCP library. This will eliminate schema compatibility issues between Claude Code and Claude Desktop.

## 🎯 Objective

- **Replace**: FastMCP server (`server.py`) with official MCP implementation
- **Maintain**: All existing functionality and API endpoints
- **Fix**: Schema validation issues with Claude Desktop
- **Ensure**: Compatibility with both Claude Code and Claude Desktop

## 📂 Project Structure

```
/Users/sudipta/Workspace/personal/AI/Smart-ToDo/
├── backend/
│   ├── mcp_server/
│   │   ├── server.py                 # ← Replace this (FastMCP)
│   │   ├── server_official.py        # ← Create this (Official MCP)
│   │   ├── client_wrapper.py         # ← Keep (with schema filtering)
│   │   ├── auth.py                   # ← Keep
│   │   ├── smart_task_parser.py      # ← Keep
│   │   └── requirements.txt          # ← Update
│   └── app/                          # ← API backend (keep)
```

## 🚀 Step-by-Step Implementation

### Step 1: Backup Current Implementation

```bash
cd /Users/sudipta/Workspace/personal/AI/Smart-ToDo/backend/mcp_server

# Create backup
cp server.py server_fastmcp_backup.py
cp requirements.txt requirements_fastmcp_backup.txt

# Verify backup
ls -la *backup*
```

### Step 2: Update Requirements

Create new `requirements.txt` with official MCP library:

```bash
# Replace fastmcp with official mcp
cat > requirements.txt << 'EOF'
# Official MCP Library (replaces fastmcp)
mcp>=1.9.4

# HTTP client for API calls
httpx>=0.24.0

# Async support
anyio>=3.6.0

# JSON schema validation
jsonschema>=4.17.0

# Date/time handling
python-dateutil>=2.8.0

# Logging
structlog>=22.1.0

# Keep existing dependencies if needed
pydantic>=2.0.0
uvicorn>=0.20.0
EOF
```

### Step 3: Create Official MCP Server

Create `server_official.py`:

```python
#!/usr/bin/env python3
"""
Smart-ToDo MCP Server - Official MCP Library Implementation
Replaces FastMCP to fix Claude Desktop compatibility issues
Created: 2025-07-14
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import httpx

# Official MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolRequest,
    ListToolsRequest,
    InitializeRequest,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("smart-todo-mcp")

# Configuration
API_ENDPOINT = os.environ.get("TODO_API_ENDPOINT", "http://localhost:8000/api/v1")

class SmartTodoMCPServer:
    """Official MCP Server implementation for Smart-ToDo"""
    
    def __init__(self):
        self.server = Server("Smart-ToDo MCP Server")
        self.setup_handlers()
        logger.info("Smart-ToDo MCP Server initialized with official MCP library")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers from environment"""
        headers = {
            'X-API-Key': os.environ.get('TODO_API_KEY', ''),
            'X-User-ID': os.environ.get('TODO_USER_ID', ''),
            'X-Device-ID': os.environ.get('TODO_DEVICE_ID', ''),
            'X-Device-Name': os.environ.get('TODO_DEVICE_NAME', 'MCP Client'),
            'X-Device-Type': 'mcp_agent'
        }
        
        if not headers.get('X-API-Key'):
            raise ValueError("Missing TODO_API_KEY environment variable")
            
        return headers
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """Get configured HTTP client"""
        auth_headers = self.get_auth_headers()
        
        return httpx.AsyncClient(
            base_url=API_ENDPOINT,
            headers=auth_headers,
            timeout=30.0,
            follow_redirects=True
        )

    async def get_user_lists(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """Get all lists accessible to the user"""
        try:
            # Get workspaces
            workspaces_response = await client.get("/workspaces")
            workspaces_response.raise_for_status()
            workspaces = workspaces_response.json()
            
            # Get lists for each workspace
            all_lists = []
            for workspace in workspaces:
                lists_response = await client.get(f"/workspaces/{workspace['id']}/lists")
                lists_response.raise_for_status()
                lists = lists_response.json()
                
                # Add workspace info to each list
                for lst in lists:
                    lst['workspace_name'] = workspace['name']
                    lst['workspace_id'] = workspace['id']
                    all_lists.append(lst)
            
            return all_lists
        except Exception as e:
            logger.error(f"Error fetching user lists: {e}")
            return []

    def setup_handlers(self):
        """Setup MCP handlers with clean schemas"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools - no context parameters, clean schemas"""
            return [
                Tool(
                    name="create_task",
                    description="Create a new task in Smart-ToDo with duplicate detection",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "request": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string", "description": "Task title"},
                                    "description": {"type": "string", "description": "Task description"},
                                    "list_name": {"type": "string", "description": "Name of the list to add task to"},
                                    "priority": {"type": "string", "description": "Priority: low, medium, high, urgent", "default": "medium"},
                                    "due_date": {"type": "string", "description": "Due date in ISO format"},
                                    "assigned_to": {"type": "array", "items": {"type": "string"}, "description": "List of user emails to assign", "default": []}
                                },
                                "required": ["title"]
                            }
                        },
                        "required": ["request"]
                    }
                ),
                Tool(
                    name="list_tasks",
                    description="List tasks from Smart-ToDo, filtered by workspace, list, or status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_name": {"type": "string", "description": "Workspace name"},
                            "list_name": {"type": "string", "description": "List name"},
                            "status": {"type": "string", "description": "Status filter"},
                            "limit": {"type": "integer", "description": "Number of tasks to retrieve", "default": 20}
                        }
                    }
                ),
                Tool(
                    name="update_task",
                    description="Update an existing task properties",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "request": {
                                "type": "object",
                                "properties": {
                                    "task_id": {"type": "string", "description": "Task ID to update"},
                                    "title": {"type": "string", "description": "New task title"},
                                    "description": {"type": "string", "description": "New task description"},
                                    "status": {"type": "string", "description": "New status: todo, in_progress, completed"},
                                    "priority": {"type": "string", "description": "New priority: low, medium, high, urgent"},
                                    "due_date": {"type": "string", "description": "New due date in ISO format"}
                                },
                                "required": ["task_id"]
                            }
                        },
                        "required": ["request"]
                    }
                ),
                Tool(
                    name="complete_task",
                    description="Mark a task as completed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Task ID"}
                        },
                        "required": ["task_id"]
                    }
                ),
                Tool(
                    name="delete_task",
                    description="Delete (archive) a task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Task ID"}
                        },
                        "required": ["task_id"]
                    }
                ),
                Tool(
                    name="search_tasks",
                    description="Search for tasks by text query in titles and descriptions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {"type": "integer", "description": "Number of results to return", "default": 10}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="create_list",
                    description="Create a new list in a workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "List name"},
                            "workspace_name": {"type": "string", "description": "Workspace name"},
                            "color": {"type": "string", "description": "List color", "default": "#000000"}
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="get_lists",
                    description="Get all lists organized by workspace",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="move_task",
                    description="Move a task to a different list",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Task ID"},
                            "list_name": {"type": "string", "description": "Target list name"}
                        },
                        "required": ["task_id", "list_name"]
                    }
                ),
                Tool(
                    name="get_upcoming_tasks",
                    description="Get tasks due in the next N days",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "description": "Number of days ahead to look", "default": 7}
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool calls by forwarding to the HTTP API"""
            
            try:
                logger.info(f"Tool call: {name}")
                
                async with self.get_http_client() as client:
                    # Route to appropriate handler based on tool name
                    if name == "create_task":
                        result = await self._create_task(client, arguments)
                    elif name == "list_tasks":
                        result = await self._list_tasks(client, arguments)
                    elif name == "update_task":
                        result = await self._update_task(client, arguments)
                    elif name == "complete_task":
                        result = await self._complete_task(client, arguments)
                    elif name == "delete_task":
                        result = await self._delete_task(client, arguments)
                    elif name == "search_tasks":
                        result = await self._search_tasks(client, arguments)
                    elif name == "create_list":
                        result = await self._create_list(client, arguments)
                    elif name == "get_lists":
                        result = await self._get_lists(client, arguments)
                    elif name == "move_task":
                        result = await self._move_task(client, arguments)
                    elif name == "get_upcoming_tasks":
                        result = await self._get_upcoming_tasks(client, arguments)
                    else:
                        return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                    
            except Exception as e:
                logger.error(f"Tool call failed: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Tool implementation methods
    async def _create_task(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Create task implementation"""
        request = args.get("request", {})
        
        # Find the target list
        lists = await self.get_user_lists(client)
        target_list = lists[0] if lists else None
        
        if request.get("list_name") and lists:
            for lst in lists:
                if lst['name'].lower() == request["list_name"].lower():
                    target_list = lst
                    break
        
        if not target_list:
            return {"error": "No lists available"}
        
        # Prepare task data
        task_data = {
            "title": request["title"],
            "description": request.get("description"),
            "priority": request.get("priority", "medium"),
            "task_metadata": {"created_via": "mcp"}
        }
        
        if request.get("due_date"):
            task_data["due_date"] = request["due_date"]
        
        # Create task
        response = await client.post(
            f"/lists/{target_list['id']}/tasks",
            json=task_data
        )
        
        if response.status_code == 409:
            # Handle duplicates
            conflict_data = response.json()
            duplicates = conflict_data.get("duplicates", [])
            return {
                "status": "duplicate_found",
                "duplicates": duplicates,
                "message": f"Found {len(duplicates)} potential duplicates. Force create if needed."
            }
        
        response.raise_for_status()
        task = response.json()
        
        return {
            "status": "created",
            "task": task,
            "list": target_list['name'],
            "workspace": target_list['workspace_name']
        }
    
    async def _list_tasks(self, client: httpx.AsyncClient, args: dict) -> dict:
        """List tasks implementation"""
        search_data = {"limit": args.get("limit", 20)}
        
        # Get workspaces/lists if filtering
        if args.get("workspace_name") or args.get("list_name"):
            lists = await self.get_user_lists(client)
            
            # Filter by workspace
            if args.get("workspace_name"):
                workspace_lists = [
                    l for l in lists 
                    if l['workspace_name'].lower() == args["workspace_name"].lower()
                ]
                if workspace_lists:
                    search_data["workspace_id"] = workspace_lists[0]['workspace_id']
            
            # Filter by list
            if args.get("list_name"):
                target_lists = [
                    l for l in lists
                    if l['name'].lower() == args["list_name"].lower()
                ]
                if target_lists:
                    search_data["list_ids"] = [target_lists[0]['id']]
        
        # Filter by status
        if args.get("status"):
            search_data["status"] = [args["status"]]
        
        # Search tasks
        response = await client.post("/tasks/search", json=search_data)
        response.raise_for_status()
        
        tasks = response.json()
        
        return {
            "count": len(tasks),
            "tasks": tasks
        }
    
    async def _update_task(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Update task implementation"""
        request = args.get("request", {})
        task_id = request["task_id"]
        
        # Prepare update data
        update_data = {}
        for field in ["title", "description", "status", "priority", "due_date"]:
            if field in request and request[field] is not None:
                update_data[field] = request[field]
        
        # Update task
        response = await client.put(f"/tasks/{task_id}", json=update_data)
        
        if response.status_code == 409:
            # Handle duplicates
            return {"status": "duplicate_conflict", "message": "Update would create duplicate"}
        
        response.raise_for_status()
        task = response.json()
        
        return {"status": "updated", "task": task}
    
    async def _complete_task(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Complete task implementation"""
        task_id = args["task_id"]
        
        response = await client.put(
            f"/tasks/{task_id}",
            json={"status": "completed"}
        )
        response.raise_for_status()
        
        task = response.json()
        return {"status": "completed", "task": task}
    
    async def _delete_task(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Delete task implementation"""
        task_id = args["task_id"]
        
        response = await client.delete(f"/tasks/{task_id}")
        response.raise_for_status()
        
        return {"status": "deleted", "task_id": task_id}
    
    async def _search_tasks(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Search tasks implementation"""
        search_data = {
            "query": args["query"],
            "limit": args.get("limit", 10)
        }
        
        response = await client.post("/tasks/search", json=search_data)
        response.raise_for_status()
        
        tasks = response.json()
        return {
            "count": len(tasks),
            "query": args["query"],
            "tasks": tasks
        }
    
    async def _create_list(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Create list implementation"""
        # Get workspaces
        workspaces_response = await client.get("/workspaces")
        workspaces_response.raise_for_status()
        workspaces = workspaces_response.json()
        
        if not workspaces:
            return {"error": "No workspaces available"}
        
        # Find target workspace
        target_workspace = workspaces[0]
        if args.get("workspace_name"):
            for ws in workspaces:
                if ws['name'].lower() == args["workspace_name"].lower():
                    target_workspace = ws
                    break
        
        # Create list
        list_data = {
            "name": args["name"],
            "color": args.get("color", "#000000")
        }
        
        response = await client.post(
            f"/workspaces/{target_workspace['id']}/lists",
            json=list_data
        )
        response.raise_for_status()
        
        new_list = response.json()
        return {
            "status": "created",
            "list": new_list,
            "workspace": target_workspace['name']
        }
    
    async def _get_lists(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Get lists implementation"""
        lists = await self.get_user_lists(client)
        
        # Organize by workspace
        by_workspace = {}
        for lst in lists:
            ws_name = lst['workspace_name']
            if ws_name not in by_workspace:
                by_workspace[ws_name] = []
            by_workspace[ws_name].append({
                "id": lst['id'],
                "name": lst['name'],
                "color": lst['color'],
                "task_count": lst.get('task_count', 0)
            })
        
        return {
            "count": len(lists),
            "by_workspace": by_workspace
        }
    
    async def _move_task(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Move task implementation"""
        task_id = args["task_id"]
        list_name = args["list_name"]
        
        # Find target list
        lists = await self.get_user_lists(client)
        target_list = None
        
        for lst in lists:
            if lst['name'].lower() == list_name.lower():
                target_list = lst
                break
        
        if not target_list:
            return {"error": f"List '{list_name}' not found"}
        
        # Update task with new list
        response = await client.put(
            f"/tasks/{task_id}",
            json={"list_id": target_list['id']}
        )
        response.raise_for_status()
        
        return {
            "status": "moved",
            "task_id": task_id,
            "new_list": list_name
        }
    
    async def _get_upcoming_tasks(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Get upcoming tasks implementation"""
        days = args.get("days", 7)
        
        # Calculate date range
        due_before = datetime.utcnow() + timedelta(days=days)
        
        search_data = {
            "due_before": due_before.isoformat(),
            "status": ["todo", "in_progress"],
            "limit": 50
        }
        
        response = await client.post("/tasks/search", json=search_data)
        response.raise_for_status()
        
        tasks = response.json()
        
        # Sort by due date
        tasks.sort(key=lambda t: t.get('due_date') or '9999-12-31')
        
        return {
            "count": len(tasks),
            "days": days,
            "tasks": tasks
        }

async def main():
    """Main entry point for stdio server"""
    server = SmartTodoMCPServer()
    
    # Run stdio server for Claude Desktop compatibility
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4: Test the New Server

Test the official MCP server:

```bash
cd /Users/sudipta/Workspace/personal/AI/Smart-ToDo/backend/mcp_server

# Install new dependencies
pip install -r requirements.txt

# Test the new server
python3 server_official.py

# In another terminal, test with stdin:
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0.0"}}, "id": 1}' | python3 server_official.py

# Test tools/list
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}' | python3 server_official.py
```

### Step 5: Update Claude Desktop Configuration

Update Claude Desktop to use the new official MCP server:

```json
{
  "mcpServers": {
    "Smart ToDo": {
      "command": "/usr/local/bin/python3",
      "args": ["/Users/sudipta/Workspace/personal/AI/Smart-ToDo/backend/mcp_server/server_official.py"],
      "env": {
        "TODO_API_ENDPOINT": "https://todo-mcp.sudiptadhara.in/api/v1",
        "TODO_API_KEY": "mcp_QaDmjdw0jZH4HFUZfCWH7V8qh7KkETsM6CtDb-EdtIQ",
        "TODO_USER_ID": "9f730d3c-4c8b-43e1-a5a5-271311746a34",
        "TODO_DEVICE_ID": "mcp_9f730d3c_dafa004677e5329a",
        "TODO_DEVICE_NAME": "Claude Desktop"
      }
    }
  }
}
```

### Step 6: Update Claude Code Configuration

Update Claude Code to use the new server:

```json
{
  "Smart ToDo": {
    "type": "stdio",
    "command": "/usr/local/bin/python3",
    "args": ["/Users/sudipta/Workspace/personal/AI/Smart-ToDo/backend/mcp_server/server_official.py"],
    "env": {
      "TODO_API_ENDPOINT": "https://todo-mcp.sudiptadhara.in/api/v1",
      "TODO_API_KEY": "mcp_yRoFR9ivFV2vkyRlTVZogrlB5_19jtZwR6DIPUfAJ3Y",
      "TODO_USER_ID": "9f730d3c-4c8b-43e1-a5a5-271311746a34",
      "TODO_DEVICE_ID": "mcp_9f730d3c_7871c5e11f4a95df",
      "TODO_DEVICE_NAME": "Claude Code"
    }
  }
}
```

### Step 7: Deploy to Remote Server (Optional)

If you want to keep the HTTP endpoint, deploy the new server:

```bash
# Update the remote deployment
cd /Users/sudipta/Workspace/personal/AI/Smart-ToDo/backend/mcp_server

# Replace server.py with the new implementation
cp server_official.py server.py

# Update Docker if using containers
# docker build -t smart-todo-mcp .
# docker push your-registry/smart-todo-mcp

# Or update your deployment process
```

## 🔍 Verification Steps

### 1. Test Schema Compatibility

```bash
# Test that tools/list returns clean schemas
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | python3 server_official.py | jq '.result.tools[0].inputSchema'

# Should NOT contain 'ctx' or 'context' parameters
```

### 2. Test Tool Functionality

```bash
# Test create_task
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "create_task", "arguments": {"request": {"title": "Test Task"}}}, "id": 2}' | python3 server_official.py

# Test list_tasks  
echo '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_tasks", "arguments": {}}, "id": 3}' | python3 server_official.py
```

### 3. Test with Both Clients

**Claude Desktop**: Should work without schema errors
**Claude Code**: Should work with both stdio and HTTP configurations

## 📊 Benefits of This Migration

| Aspect | FastMCP (Before) | Official MCP (After) |
|--------|------------------|---------------------|
| **Claude Desktop** | ❌ Schema errors | ✅ Clean compatibility |
| **Claude Code** | ✅ Works via HTTP | ✅ Works via stdio/HTTP |
| **Schema Validation** | ❌ Context parameters | ✅ Clean JSON schemas |
| **Standards Compliance** | ⚠️ Custom implementation | ✅ Official MCP protocol |
| **Maintenance** | ⚠️ Framework-specific | ✅ Standard library |
| **Debugging** | ❌ Complex filtering needed | ✅ Direct compatibility |

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   pip install mcp>=1.9.4 httpx anyio
   ```

2. **Authentication Errors**
   ```bash
   # Verify environment variables are set
   echo $TODO_API_KEY
   echo $TODO_USER_ID
   ```

3. **Connection Issues**
   ```bash
   # Test API endpoint directly
   curl -H "X-API-Key: $TODO_API_KEY" https://todo-mcp.sudiptadhara.in/api/v1/workspaces
   ```

### Rollback Plan

If issues occur, rollback to FastMCP:

```bash
cd /Users/sudipta/Workspace/personal/AI/Smart-ToDo/backend/mcp_server

# Restore backup
cp server_fastmcp_backup.py server.py
cp requirements_fastmcp_backup.txt requirements.txt

# Reinstall FastMCP
pip install fastmcp

# Use client_wrapper.py for Claude Desktop
# (Keep the schema filtering bridge)
```

## ✅ Success Criteria

- [ ] Claude Desktop connects without schema errors
- [ ] Claude Code works with both stdio and HTTP  
- [ ] All 10 tools (create_task, list_tasks, etc.) function correctly
- [ ] No `ctx` or `context` parameters in tool schemas
- [ ] Clean MCP protocol compliance
- [ ] Existing API functionality preserved

## 📝 Notes

- **Keep client_wrapper.py**: Still useful as a fallback bridge
- **Environment Variables**: Same authentication flow
- **API Endpoints**: Same backend API, just different MCP layer
- **Backward Compatibility**: Can maintain both servers during transition

## 🎯 Final Outcome

After this migration:
- **No more schema filtering needed**
- **Universal Claude compatibility**  
- **Standard MCP protocol compliance**
- **Simplified maintenance**
- **Better debugging experience**

The official MCP library handles all the protocol details correctly, eliminating the need for complex schema filtering and ensuring compatibility with all MCP clients.
