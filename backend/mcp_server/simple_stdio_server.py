#!/usr/bin/env python3
"""
Simple STDIO MCP Server for Smart-ToDo application
Uses standard MCP library without FastMCP to avoid dependency issues
Created: 2025-07-04 20:25:00 PST
"""

import os
import sys
import json
import asyncio
import httpx
from typing import Dict, Any, Optional, List
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration from environment
API_ENDPOINT = os.environ.get("TODO_API_ENDPOINT", "http://localhost:8000/api/v1")
API_KEY = os.environ.get("TODO_API_KEY", "")
DEVICE_ID = os.environ.get("TODO_DEVICE_ID", "")
DEVICE_NAME = os.environ.get("TODO_DEVICE_NAME", "MCP Agent")
USER_ID = os.environ.get("TODO_USER_ID", "")


def get_http_client() -> httpx.AsyncClient:
    """Get configured HTTP client with proper authentication"""
    headers = {}
    
    if API_KEY:
        headers = {
            "X-API-Key": API_KEY,
            "X-Device-ID": DEVICE_ID,
            "X-Device-Name": DEVICE_NAME,
            "X-User-ID": USER_ID,
            "X-Device-Type": "mcp_agent"
        }
    
    return httpx.AsyncClient(
        base_url=API_ENDPOINT,
        headers=headers,
        timeout=30.0,
        follow_redirects=True
    )


async def get_user_lists(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Get all lists accessible to the user"""
    try:
        # First get workspaces
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
        logger.error(f"Error getting user lists: {e}")
        return []


class SimpleMCPServer:
    """Simple MCP server implementation"""
    
    def __init__(self):
        self.tools = {
            "list_tasks": self.list_tasks,
            "search_tasks": self.search_tasks,
            "create_task": self.create_task,
            "update_task": self.update_task,
            "complete_task": self.complete_task,
            "get_lists": self.get_lists,
        }
        
        self.resources = {
            "tasks://recent": self.get_recent_tasks_resource,
        }
        
        self.prompts = {
            "daily_planning": self.daily_planning_prompt,
        }
    
    async def handle_initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request"""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"listChanged": True, "subscribe": False},
                    "prompts": {"listChanged": True}
                },
                "serverInfo": {
                    "name": "Smart-ToDo MCP Server",
                    "version": "1.0.0"
                }
            }
        }
    
    async def handle_tools_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools_list = [
            {
                "name": "list_tasks",
                "description": "List tasks from Smart-ToDo with optional filtering",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_name": {"type": "string", "description": "Filter by workspace name"},
                        "list_name": {"type": "string", "description": "Filter by list name"},
                        "status": {"type": "string", "description": "Filter by status (todo, in_progress, completed)"},
                        "limit": {"type": "integer", "description": "Maximum number of tasks to return", "default": 20}
                    }
                }
            },
            {
                "name": "search_tasks",
                "description": "Search for tasks by text query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_task",
                "description": "Create a new task in Smart-ToDo",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "description": {"type": "string", "description": "Task description"},
                        "list_name": {"type": "string", "description": "Name of the list to add task to"},
                        "priority": {"type": "string", "description": "Priority: low, medium, high, urgent", "default": "medium"},
                        "due_date": {"type": "string", "description": "Due date in ISO format"}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "update_task",
                "description": "Update an existing task",
                "inputSchema": {
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
            {
                "name": "complete_task",
                "description": "Mark a task as completed",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID to complete"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "get_lists",
                "description": "Get all lists organized by workspace",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": tools_list
            }
        }
    
    async def handle_resources_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources_list = [
            {
                "uri": "tasks://recent",
                "name": "Recent Tasks",
                "description": "Recently modified tasks",
                "mimeType": "text/plain"
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "resources": resources_list
            }
        }
    
    async def handle_prompts_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request"""
        prompts_list = [
            {
                "name": "daily_planning",
                "description": "Prompt for daily task planning"
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "prompts": prompts_list
            }
        }
    
    async def handle_tools_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        try:
            params = request.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name not in self.tools:
                raise Exception(f"Unknown tool: {tool_name}")
            
            result = await self.tools[tool_name](**arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    # Tool implementations
    async def list_tasks(self, workspace_name: Optional[str] = None, list_name: Optional[str] = None, 
                        status: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """List tasks from Smart-ToDo"""
        async with get_http_client() as client:
            # Build search query
            search_data = {"limit": limit}
            
            # Get workspaces/lists if filtering
            if workspace_name or list_name:
                lists = await get_user_lists(client)
                
                # Filter by workspace
                if workspace_name:
                    workspace_lists = [
                        l for l in lists 
                        if l['workspace_name'].lower() == workspace_name.lower()
                    ]
                    if workspace_lists:
                        search_data["workspace_id"] = workspace_lists[0]['workspace_id']
                
                # Filter by list
                if list_name:
                    target_lists = [
                        l for l in lists
                        if l['name'].lower() == list_name.lower()
                    ]
                    if target_lists:
                        search_data["list_ids"] = [target_lists[0]['id']]
            
            # Filter by status
            if status:
                search_data["status"] = [status]
            
            # Search tasks
            response = await client.post("/tasks/search", json=search_data)
            response.raise_for_status()
            
            tasks = response.json()
            
            return {
                "count": len(tasks),
                "tasks": tasks
            }
    
    async def search_tasks(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for tasks by text query"""
        async with get_http_client() as client:
            search_data = {
                "query": query,
                "limit": limit
            }
            
            response = await client.post("/tasks/search", json=search_data)
            response.raise_for_status()
            
            tasks = response.json()
            
            return {
                "count": len(tasks),
                "query": query,
                "tasks": tasks
            }
    
    async def create_task(self, title: str, description: Optional[str] = None, 
                         list_name: Optional[str] = None, priority: str = "medium",
                         due_date: Optional[str] = None) -> Dict[str, Any]:
        """Create a new task in Smart-ToDo"""
        async with get_http_client() as client:
            # Find the target list
            lists = await get_user_lists(client)
            
            # Default to first list or find by name
            target_list = lists[0] if lists else None
            if list_name and lists:
                for lst in lists:
                    if lst['name'].lower() == list_name.lower():
                        target_list = lst
                        break
            
            if not target_list:
                return {"error": "No lists available"}
            
            # Prepare task data
            task_data = {
                "title": title,
                "description": description,
                "priority": priority,
                "metadata": {"created_via": "mcp"}
            }
            
            if due_date:
                task_data["due_date"] = due_date
            
            # Create task
            response = await client.post(
                f"/lists/{target_list['id']}/tasks",
                json=task_data
            )
            
            if response.status_code == 409:
                conflict_data = response.json()
                duplicates = conflict_data.get("duplicates", [])
                return {
                    "status": "duplicate_found",
                    "message": f"Found {len(duplicates)} potential duplicate(s)",
                    "duplicates": duplicates
                }
            
            response.raise_for_status()
            task = response.json()
            
            return {
                "status": "created",
                "task": task,
                "list": target_list['name'],
                "workspace": target_list['workspace_name']
            }
    
    async def update_task(self, task_id: str, title: Optional[str] = None,
                         description: Optional[str] = None, status: Optional[str] = None,
                         priority: Optional[str] = None, due_date: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing task"""
        async with get_http_client() as client:
            # Prepare update data
            update_data = {}
            if title is not None:
                update_data["title"] = title
            if description is not None:
                update_data["description"] = description
            if status is not None:
                update_data["status"] = status
            if priority is not None:
                update_data["priority"] = priority
            if due_date is not None:
                update_data["due_date"] = due_date
            
            # Update task
            response = await client.put(f"/tasks/{task_id}", json=update_data)
            response.raise_for_status()
            task = response.json()
            
            return {
                "status": "updated",
                "task": task
            }
    
    async def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as completed"""
        return await self.update_task(task_id, status="completed")
    
    async def get_lists(self) -> Dict[str, Any]:
        """Get all lists organized by workspace"""
        async with get_http_client() as client:
            lists = await get_user_lists(client)
            
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
    
    async def get_recent_tasks_resource(self) -> str:
        """Get recently modified tasks"""
        result = await self.list_tasks(limit=10)
        
        if not result.get('tasks'):
            return "No recent tasks found."
        
        lines = ["Recently modified tasks:\\n"]
        for task in result['tasks']:
            status = "✓" if task['status'] == "completed" else "○"
            lines.append(f"{status} {task['title']} (Priority: {task['priority']})")
            if task.get('due_date'):
                lines.append(f"  Due: {task['due_date']}")
            if task.get('description'):
                lines.append(f"  {task['description'][:100]}...")
            lines.append("")
        
        return "\\n".join(lines)
    
    def daily_planning_prompt(self) -> str:
        """Prompt for daily task planning"""
        return """Please help me plan my day by:

1. First, list all my tasks that are due today or overdue
2. Then, show my high-priority tasks that aren't due today
3. Suggest a reasonable order to tackle these tasks
4. Ask if I'd like to add any new tasks for today

Use the available tools to fetch and organize my tasks."""
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        method = request.get("method")
        
        try:
            if method == "initialize":
                return await self.handle_initialize(request)
            elif method == "notifications/initialized":
                # No response needed for notifications
                return None
            elif method == "tools/list":
                return await self.handle_tools_list(request)
            elif method == "resources/list":
                return await self.handle_resources_list(request)
            elif method == "prompts/list":
                return await self.handle_prompts_list(request)
            elif method == "tools/call":
                return await self.handle_tools_call(request)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
        except Exception as e:
            logger.error(f"Error handling request {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def run(self):
        """Run the MCP server with stdio transport"""
        logger.info("Starting Simple MCP Server for Smart-ToDo")
        
        try:
            while True:
                # Read from stdin
                line = sys.stdin.readline()
                if not line:  # EOF
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)
                    
                    if response:  # Some methods don't need responses
                        response_line = json.dumps(response, separators=(',', ':'))
                        print(response_line, flush=True)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    continue
                    
        except KeyboardInterrupt:
            logger.info("Server interrupted")
        except Exception as e:
            logger.error(f"Server error: {e}")
        
        logger.info("MCP Server shutting down")


async def main():
    """Main entry point"""
    server = SimpleMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())