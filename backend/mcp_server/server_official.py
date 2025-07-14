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

# Import smart task parser (reuse existing)
from smart_task_parser import SmartTaskParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("smart-todo-mcp")

# Configuration
API_ENDPOINT = os.environ.get("TODO_API_ENDPOINT", "https://todo-api.sudiptadhara.in/api/v1")

class SmartTodoMCPServer:
    """Official MCP Server implementation for Smart-ToDo"""
    
    def __init__(self):
        self.server = Server("Smart-ToDo MCP Server")
        self.smart_parser = SmartTaskParser()
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
                            "title": {"type": "string", "description": "Task title"},
                            "description": {"type": "string", "description": "Task description"},
                            "list_name": {"type": "string", "description": "Name of the list to add task to"},
                            "priority": {"type": "string", "description": "Priority: low, medium, high, urgent", "default": "medium"},
                            "due_date": {"type": "string", "description": "Due date in ISO format"},
                            "assigned_to": {"type": "array", "items": {"type": "string"}, "description": "List of user emails to assign", "default": []}
                        },
                        "required": ["title"]
                    }
                ),
                Tool(
                    name="smart_create_task",
                    description="Create a task using natural language (e.g., 'Buy milk tomorrow at 5pm high priority')",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Natural language task description"}
                        },
                        "required": ["text"]
                    }
                ),
                Tool(
                    name="list_tasks",
                    description="List tasks from Smart-ToDo, filtered by workspace, list, or status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace": {"type": "string", "description": "Workspace name"},
                            "list": {"type": "string", "description": "List name"},
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
                            "task_id": {"type": "string", "description": "Task ID to update"},
                            "title": {"type": "string", "description": "New task title"},
                            "description": {"type": "string", "description": "New task description"},
                            "status": {"type": "string", "description": "New status: todo, in_progress, completed"},
                            "priority": {"type": "string", "description": "New priority: low, medium, high, urgent"},
                            "due_date": {"type": "string", "description": "New due date in ISO format"}
                        },
                        "required": ["task_id"]
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
                    name="get_task",
                    description="Get detailed information about a specific task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Task ID"}
                        },
                        "required": ["task_id"]
                    }
                ),
                Tool(
                    name="list_workspaces",
                    description="List all available workspaces",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="list_lists",
                    description="List all lists, optionally filtered by workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_id": {"type": "string", "description": "Workspace ID to filter lists"}
                        }
                    }
                ),
                Tool(
                    name="get_stats",
                    description="Get task statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_id": {"type": "string", "description": "Workspace ID for stats"}
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool calls by forwarding to the HTTP API"""
            
            try:
                logger.info(f"Tool call: {name} with args: {arguments}")
                
                async with await self.get_http_client() as client:
                    # Route to appropriate handler based on tool name
                    if name == "create_task":
                        result = await self._create_task(client, arguments)
                    elif name == "smart_create_task":
                        result = await self._smart_create_task(client, arguments)
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
                    elif name == "get_task":
                        result = await self._get_task(client, arguments)
                    elif name == "list_workspaces":
                        result = await self._list_workspaces(client, arguments)
                    elif name == "list_lists":
                        result = await self._list_lists(client, arguments)
                    elif name == "get_stats":
                        result = await self._get_stats(client, arguments)
                    else:
                        return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                    
            except Exception as e:
                logger.error(f"Tool call failed: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Tool implementation methods
    async def _create_task(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Create task implementation"""
        # Find the target list
        lists = await self.get_user_lists(client)
        target_list = lists[0] if lists else None
        
        if args.get("list_name") and lists:
            for lst in lists:
                if lst['name'].lower() == args["list_name"].lower():
                    target_list = lst
                    break
        
        if not target_list:
            return {"error": "No lists available"}
        
        # Prepare task data
        task_data = {
            "title": args["title"],
            "description": args.get("description"),
            "priority": args.get("priority", "medium"),
            "task_metadata": {"created_via": "mcp"}
        }
        
        if args.get("due_date"):
            task_data["due_date"] = args["due_date"]
        
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
    
    async def _smart_create_task(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Smart create task using natural language"""
        text = args["text"]
        
        # Parse the natural language text
        parsed = self.smart_parser.parse(text)
        
        # Create task with parsed data
        return await self._create_task(client, {
            "title": parsed["title"],
            "description": parsed.get("description"),
            "priority": parsed.get("priority", "medium"),
            "due_date": parsed.get("due_date"),
            "list_name": parsed.get("list_name")
        })
    
    async def _list_tasks(self, client: httpx.AsyncClient, args: dict) -> dict:
        """List tasks implementation"""
        search_data = {"limit": args.get("limit", 20)}
        
        # Get workspaces/lists if filtering
        if args.get("workspace") or args.get("list"):
            lists = await self.get_user_lists(client)
            
            # Filter by workspace
            if args.get("workspace"):
                workspace_lists = [
                    l for l in lists 
                    if l['workspace_name'].lower() == args["workspace"].lower()
                ]
                if workspace_lists:
                    search_data["workspace_id"] = workspace_lists[0]['workspace_id']
            
            # Filter by list
            if args.get("list"):
                target_lists = [
                    l for l in lists
                    if l['name'].lower() == args["list"].lower()
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
        task_id = args["task_id"]
        
        # Prepare update data
        update_data = {}
        for field in ["title", "description", "status", "priority", "due_date"]:
            if field in args and args[field] is not None:
                update_data[field] = args[field]
        
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
    
    async def _get_task(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Get task details implementation"""
        task_id = args["task_id"]
        
        response = await client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        
        return response.json()
    
    async def _list_workspaces(self, client: httpx.AsyncClient, args: dict) -> dict:
        """List workspaces implementation"""
        response = await client.get("/workspaces")
        response.raise_for_status()
        
        workspaces = response.json()
        return {
            "count": len(workspaces),
            "workspaces": workspaces
        }
    
    async def _list_lists(self, client: httpx.AsyncClient, args: dict) -> dict:
        """List lists implementation"""
        workspace_id = args.get("workspace_id")
        
        if workspace_id:
            # Get lists for specific workspace
            response = await client.get(f"/workspaces/{workspace_id}/lists")
            response.raise_for_status()
            lists = response.json()
            
            return {
                "count": len(lists),
                "lists": lists,
                "workspace_id": workspace_id
            }
        else:
            # Get all lists
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
    
    async def _get_stats(self, client: httpx.AsyncClient, args: dict) -> dict:
        """Get stats implementation"""
        workspace_id = args.get("workspace_id")
        
        # Build stats endpoint URL
        endpoint = "/stats"
        if workspace_id:
            endpoint = f"/workspaces/{workspace_id}/stats"
        
        response = await client.get(endpoint)
        response.raise_for_status()
        
        return response.json()

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