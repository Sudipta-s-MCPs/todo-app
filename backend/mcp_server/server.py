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
from starlette.applications import Starlette

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import smart task parser (now self-contained)
from .smart_task_parser import SmartTaskParser

# Import auth manager
from .auth import MCPAuthManager

# Configuration from environment
API_ENDPOINT = os.environ.get("TODO_API_ENDPOINT", "http://localhost:8000/api/v1")

# Initialize auth manager
auth_manager = MCPAuthManager()

# Thread-local storage for request headers
import threading
request_context = threading.local()

# Log environment variables at startup
logger.info(f"API Endpoint: {API_ENDPOINT}")
logger.info(f"TODO_API_KEY present: {'TODO_API_KEY' in os.environ}")
logger.info(f"TODO_USER_ID present: {'TODO_USER_ID' in os.environ}")
logger.info(f"TODO_DEVICE_ID present: {'TODO_DEVICE_ID' in os.environ}")


# Authentication middleware for FastMCP
class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate MCP requests"""
    
    async def dispatch(self, request, call_next):
        # Skip authentication for health endpoint only
        if request.url.path == "/health":
            return await call_next(request)
        
        # Log incoming headers for debugging
        logger.info(f"Incoming request to {request.url.path}")
        logger.debug(f"Headers: {dict(request.headers)}")
        
        # Check for API key in X-API-Key header
        api_key = request.headers.get('x-api-key', '')
        
        if api_key:
            logger.info(f"Received API key ending in: ...{api_key[-4:] if len(api_key) > 4 else api_key}")
        else:
            logger.warning("No X-API-Key header in request")
        
        # For MCP, we validate the API key exists and pass it through
        # The backend will validate if it's correct
        if api_key:
            logger.info("API key authentication successful")
            # Store auth info in request state and thread-local for tools to use
            auth_headers = {
                "X-API-Key": api_key,
                "X-User-ID": request.headers.get('x-user-id', ''),
                "X-Device-ID": request.headers.get('x-device-id', ''),
                "X-Device-Name": request.headers.get('x-device-name', 'MCP Agent'),
                "X-Device-Type": "mcp_agent"
            }
            request.state.auth_headers = auth_headers
            request_context.auth_headers = auth_headers  # Store in thread-local
            
            try:
                response = await call_next(request)
                return response
            finally:
                # Clean up thread-local storage
                if hasattr(request_context, 'auth_headers'):
                    delattr(request_context, 'auth_headers')
        
        # Check for Bearer token
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            logger.info("Attempting Bearer token authentication")
            # Validate OAuth token
            if await auth_manager.validate_oauth_token(token):
                logger.info("Bearer token authentication successful")
                return await call_next(request)
            else:
                logger.warning("Bearer token validation failed")
        
        # Authentication failed
        logger.error(f"Authentication failed for request to {request.url.path}")
        return JSONResponse(
            {"detail": "Invalid or missing authorization"},
            status_code=401,
        )


# Extend FastMCP to add authentication middleware
class AuthenticatedFastMCP(FastMCP):
    """FastMCP server with authentication middleware"""
    
    def get_app(self) -> Starlette:
        """Get the Starlette app with authentication middleware"""
        app = super().get_app()
        app.add_middleware(AuthMiddleware)
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
    
    def __init__(self, base_url: str, auth_manager: MCPAuthManager, auth_headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_manager = auth_manager
        self.auth_headers = auth_headers  # Headers from the incoming request
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(base_url=self.base_url)
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


def get_http_client(ctx: Context = None) -> AuthenticatedHttpClient:
    """Get authenticated HTTP client with request headers from context"""
    auth_headers = None
    
    # Try to get auth headers from thread-local storage
    if hasattr(request_context, 'auth_headers'):
        auth_headers = request_context.auth_headers
        logger.debug(f"Got auth headers from thread-local: {auth_headers}")
    
    return AuthenticatedHttpClient(API_ENDPOINT, auth_manager, auth_headers)


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
        response = await client.get("/tasks", params=params)
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
        response = await client.get("/workspaces")
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


# The authentication middleware is now defined at the top of the file


if __name__ == "__main__":
    # Run the MCP server with HTTP transport
    # Bind to all interfaces for Docker accessibility
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=5485
    )