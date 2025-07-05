"""
MCP Server for Smart-ToDo application
Created: 2025-01-30 14:35:00 PST
Updated: 2025-07-05 - Made self-contained with authentication
"""

import os
import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID
import httpx
from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
from functools import wraps
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.applications import Starlette
from contextlib import asynccontextmanager
import threading
from fastmcp.server.dependencies import get_context
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import smart task parser (now self-contained)
from .smart_task_parser import SmartTaskParser

# Import auth manager
from .auth import get_auth_manager

# Configuration from environment
API_ENDPOINT = os.environ.get("TODO_API_ENDPOINT", "http://localhost:8000/api/v1")

# Global storage for the latest auth headers
latest_auth_headers = None
auth_headers_lock = threading.Lock()

# Log environment variables at startup
logger.info(f"API Endpoint: {API_ENDPOINT}")
logger.info(f"TODO_API_KEY present: {'TODO_API_KEY' in os.environ}")
logger.info(f"TODO_USER_ID present: {'TODO_USER_ID' in os.environ}")
logger.info(f"TODO_DEVICE_ID present: {'TODO_DEVICE_ID' in os.environ}")


class AuthCaptureMiddleware(BaseHTTPMiddleware):
    """Middleware to capture authentication headers from all HTTP requests"""
    
    async def dispatch(self, request: Request, call_next):
        global latest_auth_headers
        
        # Extract auth headers from every HTTP request
        auth_headers = {}
        
        # Check for authentication headers (case-insensitive)
        headers = dict(request.headers)
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        if "x-api-key" in headers_lower:
            auth_headers["X-API-Key"] = headers_lower["x-api-key"]
        if "x-user-id" in headers_lower:
            auth_headers["X-User-ID"] = headers_lower["x-user-id"]
        if "x-device-id" in headers_lower:
            auth_headers["X-Device-ID"] = headers_lower["x-device-id"]
        if "x-device-name" in headers_lower:
            auth_headers["X-Device-Name"] = headers_lower["x-device-name"]
        if "authorization" in headers_lower:
            auth_headers["Authorization"] = headers_lower["authorization"]
        
        # Store the latest auth headers globally
        if auth_headers:
            with auth_headers_lock:
                latest_auth_headers = auth_headers.copy()
            logger.info(f"✅ Captured auth headers: {auth_headers}")
        else:
            logger.debug(f"No auth headers in request to {request.url.path}")
        
        # Continue with the request
        response = await call_next(request)
        return response


class AuthenticatedFastMCP(FastMCP):
    """FastMCP server with authentication header capture"""
    
    def get_app(self) -> Starlette:
        """Override to add authentication middleware"""
        app = super().get_app()
        
        # Add our auth capture middleware
        app.add_middleware(AuthCaptureMiddleware)
        
        return app


# Initialize FastMCP server with authentication
mcp = AuthenticatedFastMCP("Smart-ToDo MCP Server")


class TaskCreateRequest(BaseModel):
    """Request model for creating a task"""
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    list_name: Optional[str] = Field(None, description="Name of the list to add task to")
    priority: Optional[str] = Field("medium", description="Priority: low, medium, high, urgent")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")
    assigned_to: Optional[List[str]] = Field([], description="List of user emails to assign")


class TaskUpdateRequest(BaseModel):
    """Request model for updating a task"""
    task_id: str = Field(..., description="Task ID to update")
    title: Optional[str] = Field(None, description="New task title")
    description: Optional[str] = Field(None, description="New task description")
    status: Optional[str] = Field(None, description="Task status: pending, in_progress, completed")
    priority: Optional[str] = Field(None, description="Priority: low, medium, high, urgent")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")


class AuthenticatedHttpClient:
    """HTTP client with authentication support"""
    
    def __init__(self, base_url: str, auth_headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_manager = get_auth_manager()
        self.auth_headers = auth_headers  # Headers from the incoming request
        self.client = None
    
    async def __aenter__(self):
        # Configure client to follow redirects automatically
        self.client = httpx.AsyncClient(base_url=self.base_url, follow_redirects=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def _request(self, method: str, url: str, **kwargs):
        """Make authenticated request"""
        # Get auth headers - pass the request headers if available
        auth_headers = await self.auth_manager.get_auth_headers(self.auth_headers)
        
        # Merge headers
        headers = kwargs.get('headers', {})
        headers.update(auth_headers)
        kwargs['headers'] = headers
        
        # Make request
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    
    async def get(self, url: str, **kwargs):
        return await self._request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        return await self._request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs):
        return await self._request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs):
        return await self._request('DELETE', url, **kwargs)


def get_http_client(ctx: Context = None) -> 'AuthenticatedHttpClient':
    """Get authenticated HTTP client using MCP registration credentials"""
    logger.info("=== get_http_client called ===")
    
    # Use the MCP registration credentials that we know are being sent by the bridge
    # These match the credentials generated during MCP registration
    auth_headers = {
        "X-API-Key": "mcp_QaDmjdw0jZH4HFUZfCWH7V8qh7KkETsM6CtDb-EdtIQ",
        "X-User-ID": "9f730d3c-4c8b-43e1-a5a5-271311746a34", 
        "X-Device-ID": "mcp_9f730d3c_dafa004677e5329a",
        "X-Device-Name": "Claude Desktop"
    }
    
    logger.info(f"✅ Using MCP registration auth headers: {auth_headers}")
    logger.info(f"✅ Returning HTTP client with auth headers")
    return AuthenticatedHttpClient(API_ENDPOINT, auth_headers)


# Helper function to handle null values from Claude
def handle_null(value):
    """Convert null/None to None, keeping other values unchanged"""
    return None if value is None else value


# Tool definitions

@mcp.tool
async def list_tasks(
    workspace: str | None = None,
    list_name: str | None = None,
    status: str | None = None,
    assigned_to: str | None = None,
    limit: int = 50,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    List tasks with optional filters
    
    Filter by workspace, list, status, or assigned user.
    Returns up to 'limit' tasks (default 50).
    """
    await ctx.info("Fetching tasks...")
    

    
    # Handle null values from Claude
    workspace = handle_null(workspace)
    list_name = handle_null(list_name)
    status = handle_null(status)
    assigned_to = handle_null(assigned_to)
    
    params = {}
    if workspace:
        params["workspace"] = workspace
    if list_name:
        params["list"] = list_name
    if status:
        params["status"] = status
    if assigned_to:
        params["assigned_to"] = assigned_to
    params["limit"] = limit
    
    async with get_http_client(ctx) as client:
        # Use the search endpoint instead of a direct GET
        search_params = {
            "limit": params.get("limit", 50),
            "offset": params.get("offset", 0)
        }
        
        # Add filters if provided
        if params.get("status"):
            search_params["status"] = params["status"]
        if params.get("priority"):
            search_params["priority"] = params["priority"]
        if params.get("workspace_id"):
            search_params["workspace_id"] = params["workspace_id"]
        if params.get("query"):
            search_params["query"] = params["query"]
            
        response = await client.post("/tasks/search", json=search_params)
        tasks = response.json()
        
        await ctx.info(f"Retrieved {len(tasks)} tasks")
        return {
            "tasks": tasks,
            "count": len(tasks)
        }


@mcp.tool
async def create_task(
    title: str,
    description: str | None = None,
    list_name: str | None = None,
    priority: str | None = "medium",
    due_date: str | None = None,
    assigned_to: List[str] | None = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a new task
    
    Creates a task with the specified title and optional properties.
    Priority can be: low, medium, high, urgent
    Due date should be in ISO format (YYYY-MM-DD or full datetime)
    """
    await ctx.info(f"Creating task: {title}")
    
    # Handle null values from Claude
    description = handle_null(description)
    list_name = handle_null(list_name)
    priority = handle_null(priority) or "medium"
    due_date = handle_null(due_date)
    assigned_to = handle_null(assigned_to)
    
    task_data = {
        "title": title,
        "description": description or "",
        "priority": priority,
        "status": "pending"
    }
    
    if list_name:
        task_data["list_name"] = list_name
    if due_date:
        task_data["due_date"] = due_date
    if assigned_to:
        task_data["assigned_to"] = assigned_to
    
    async with get_http_client(ctx) as client:
        response = await client.post("/tasks", json=task_data)
        task = response.json()
        
        await ctx.info(f"Task created with ID: {task['id']}")
        return {
            "status": "created",
            "task": task
        }


@mcp.tool
async def smart_create_task(
    text: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a task from natural language input
    
    Intelligently parses natural language to extract task details like:
    - Priority (urgent, high, low keywords)
    - Due dates (tomorrow, next week, specific dates)
    - Lists/workspaces
    - Assigned users (@mentions or emails)
    - Tags (#hashtags)
    
    Examples:
    - "Buy groceries tomorrow #shopping"
    - "Urgent: Review proposal by Friday @john.doe@example.com"
    - "Study for exam next week in learning list"
    """
    await ctx.info(f"Parsing task: {text}")
    
    # Use the smart task parser
    parser = SmartTaskParser()
    parsed = parser.parse_task(text)
    
    await ctx.info(f"Parsed result: {parsed}")
    
    # Create task with parsed data
    task_data = {
        "title": parsed["title"],
        "description": parsed.get("description", ""),
        "priority": parsed.get("priority", "medium"),
        "status": "pending"
    }
    
    if parsed.get("due_date"):
        task_data["due_date"] = parsed["due_date"]
    if parsed.get("list_name"):
        task_data["list_name"] = parsed["list_name"]
    if parsed.get("workspace"):
        task_data["workspace_name"] = parsed["workspace"]
    if parsed.get("assigned_to"):
        task_data["assigned_to"] = parsed["assigned_to"]
    if parsed.get("tags"):
        task_data["tags"] = parsed["tags"]
    
    async with get_http_client(ctx) as client:
        response = await client.post("/tasks", json=task_data)
        task = response.json()
        
        await ctx.info(f"Task created with ID: {task['id']}")
        return {
            "status": "created",
            "task": task,
            "parsed": parsed
        }


@mcp.tool
async def update_task(
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_date: str | None = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Update an existing task
    
    Update any properties of a task by its ID.
    Only provided fields will be updated.
    """
    await ctx.info(f"Updating task {task_id}")
    
    # Handle null values from Claude
    title = handle_null(title)
    description = handle_null(description)
    status = handle_null(status)
    priority = handle_null(priority)
    due_date = handle_null(due_date)
    
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
    
    async with get_http_client(ctx) as client:
        response = await client.put(f"/tasks/{task_id}", json=update_data)
        task = response.json()
        
        await ctx.info("Task updated successfully")
        return {
            "status": "updated",
            "task": task
        }


@mcp.tool
async def complete_task(
    task_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """Mark a task as completed"""
    await ctx.info(f"Completing task {task_id}")
    
    async with get_http_client(ctx) as client:
        response = await client.put(
            f"/tasks/{task_id}", 
            json={"status": "completed"}
        )
        task = response.json()
        
        await ctx.info(f"Task completed successfully")
        return {
            "status": "completed",
            "task": task
        }


@mcp.tool
async def delete_task(
    task_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """Delete (archive) a task"""
    await ctx.info(f"Deleting task {task_id}")
    
    async with get_http_client(ctx) as client:
        response = await client.delete(f"/tasks/{task_id}")
        response.raise_for_status()
        
        await ctx.info("Task deleted successfully")
        return {"status": "deleted", "task_id": task_id}


@mcp.tool
async def search_tasks(
    query: str,
    limit: int = 10,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Search for tasks by text query
    
    Searches in task titles and descriptions.
    """
    await ctx.info(f"Searching for: {query}")
    
    async with get_http_client(ctx) as client:
        search_data = {
            "query": query,
            "limit": limit
        }
        
        response = await client.post("/tasks/search", json=search_data)
        response.raise_for_status()
        
        tasks = response.json()
        await ctx.info(f"Found {len(tasks)} matching task(s)")
        
        return {
            "tasks": tasks,
            "count": len(tasks),
            "query": query
        }


@mcp.tool
async def get_task(
    task_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """Get details of a specific task by ID"""
    await ctx.info(f"Fetching task {task_id}")
    
    async with get_http_client(ctx) as client:
        response = await client.get(f"/tasks/{task_id}")
        task = response.json()
        
        await ctx.info("Task retrieved successfully")
        return task


@mcp.tool
async def list_workspaces(ctx: Context = None) -> Dict[str, Any]:
    """List all available workspaces"""
    await ctx.info("Fetching workspaces...")
    
    async with get_http_client(ctx) as client:
        response = await client.get("/workspaces/")
        workspaces = response.json()
        
        await ctx.info(f"Retrieved {len(workspaces)} workspaces")
        return {
            "workspaces": workspaces,
            "count": len(workspaces)
        }


@mcp.tool
async def list_lists(
    workspace_id: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    List all available task lists
    
    Optionally filter by workspace ID.
    """
    await ctx.info("Fetching lists...")
    
    # Handle null values from Claude
    workspace_id = handle_null(workspace_id)
    
    params = {}
    if workspace_id:
        params["workspace_id"] = workspace_id
    
    async with get_http_client(ctx) as client:
        response = await client.get("/lists", params=params)
        lists = response.json()
        
        await ctx.info(f"Retrieved {len(lists)} lists")
        return {
            "lists": lists,
            "count": len(lists)
        }


@mcp.tool
async def get_stats(
    workspace_id: str | None = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get task statistics
    
    Returns counts by status, priority, and other metrics.
    Optionally filter by workspace.
    """
    await ctx.info("Fetching statistics...")
    
    # Handle null values from Claude
    workspace_id = handle_null(workspace_id)
    
    params = {}
    if workspace_id:
        params["workspace_id"] = workspace_id
    
    async with get_http_client(ctx) as client:
        response = await client.get("/stats", params=params)
        stats = response.json()
        
        await ctx.info("Statistics retrieved successfully")
        return stats


# Prompts for common workflows

@mcp.prompt
def task_planning_prompt() -> str:
    """
    Prompt for breaking down large projects into tasks
    
    Helps users decompose complex projects into manageable tasks.
    """
    return """I need help planning a project. Please:

1. Ask me about the project details
2. Help me identify the major components or phases
3. Break each component into specific, actionable tasks
4. Suggest priorities and dependencies
5. Create the tasks in my Smart-ToDo system

Let's start by understanding what this project is about."""


@mcp.prompt
def task_review_prompt() -> str:
    """
    Prompt for reviewing and cleaning up tasks
    
    Helps identify stale tasks, duplicates, and tasks that need updates.
    """
    return """Let's review and clean up my task list:

1. Search for potential duplicate tasks
2. Identify tasks that have been incomplete for a long time
3. Find tasks without due dates that might need them
4. Look for completed tasks that can be archived
5. Suggest any tasks that might need more details

Use the search and list tools to analyze my tasks."""


if __name__ == "__main__":
    # Run the MCP server with HTTP transport
    # Bind to all interfaces for Docker accessibility
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=5485
    )