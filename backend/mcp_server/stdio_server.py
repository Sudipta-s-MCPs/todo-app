#!/usr/bin/env python3
"""
Direct STDIO MCP Server for Smart-ToDo application
This bypasses HTTP transport for direct Claude Desktop integration
Created: 2025-07-04 20:15:00 PST
"""

import os
import sys
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import httpx
from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import smart task parser
from .smart_task_parser import SmartTaskParser

# Initialize FastMCP server for STDIO
mcp = FastMCP("Smart-ToDo MCP Server")

# Configuration from environment
API_ENDPOINT = os.environ.get("TODO_API_ENDPOINT", "http://localhost:8000/api/v1")


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
    status: Optional[str] = Field(None, description="New status: todo, in_progress, completed")
    priority: Optional[str] = Field(None, description="New priority: low, medium, high, urgent")
    due_date: Optional[str] = Field(None, description="New due date in ISO format")


def get_http_client() -> httpx.AsyncClient:
    """Get configured HTTP client with proper authentication"""
    # Get credentials from environment (passed by client wrapper)
    headers = {}
    
    api_key = os.environ.get("TODO_API_KEY", "")
    if api_key:
        headers = {
            "X-API-Key": api_key,
            "X-Device-ID": os.environ.get("TODO_DEVICE_ID", ""),
            "X-Device-Name": os.environ.get("TODO_DEVICE_NAME", "MCP Agent"),
            "X-User-ID": os.environ.get("TODO_USER_ID", ""),
            "X-Device-Type": "mcp_agent"
        }
    
    return httpx.AsyncClient(
        base_url=API_ENDPOINT,
        headers=headers,
        timeout=30.0,
        follow_redirects=True  # Handle trailing slash redirects
    )


async def get_user_lists(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Get all lists accessible to the user"""
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


@mcp.tool
async def create_task(
    request: TaskCreateRequest,
    ctx: Context
) -> Dict[str, Any]:
    """
    Create a new task in Smart-ToDo
    
    This tool creates a new task with duplicate detection. If potential duplicates
    are found, it will ask for confirmation before creating the task.
    """
    await ctx.info(f"Creating task: {request.title}")
    
    async with get_http_client() as client:
        # Find the target list
        lists = await get_user_lists(client)
        
        # Default to first list or find by name
        target_list = lists[0] if lists else None
        if request.list_name and lists:
            for lst in lists:
                if lst['name'].lower() == request.list_name.lower():
                    target_list = lst
                    break
        
        if not target_list:
            await ctx.error("No lists found. Please create a workspace and list first.")
            return {"error": "No lists available"}
        
        # Prepare task data
        task_data = {
            "title": request.title,
            "description": request.description,
            "priority": request.priority or "medium",
            "metadata": {"created_via": "mcp"}
        }
        
        if request.due_date:
            task_data["due_date"] = request.due_date
        
        # Create task
        response = await client.post(
            f"/lists/{target_list['id']}/tasks",
            json=task_data
        )
        
        # Handle duplicate detection
        if response.status_code == 409:
            conflict_data = response.json()
            duplicates = conflict_data.get("duplicates", [])
            
            if duplicates:
                await ctx.warning(f"Found {len(duplicates)} potential duplicate(s)")
                
                # Show duplicates
                dup_info = "\\n".join([
                    f"- {d['title']} (status: {d['status']})"
                    for d in duplicates[:3]
                ])
                
                # In stdio mode, we'll return the conflict for user decision
                return {
                    "status": "duplicate_found",
                    "message": f"Potential duplicate tasks found:\\n{dup_info}\\n\\nPlease confirm if you want to create this task anyway.",
                    "duplicates": duplicates,
                    "suggested_task": task_data,
                    "target_list": target_list
                }
        
        response.raise_for_status()
        task = response.json()
        
        await ctx.info(f"Task created successfully: {task['id']}")
        return {
            "status": "created",
            "task": task,
            "list": target_list['name'],
            "workspace": target_list['workspace_name']
        }


@mcp.tool
async def list_tasks(
    workspace_name: Optional[str] = None,
    list_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    List tasks from Smart-ToDo
    
    Filter by workspace, list, or status. Returns up to 'limit' tasks.
    """
    await ctx.info("Fetching tasks...")
    
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
        
        await ctx.info(f"Found {len(tasks)} task(s)")
        
        return {
            "count": len(tasks),
            "tasks": tasks
        }


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
    
    async with get_http_client() as client:
        search_data = {
            "query": query,
            "limit": limit
        }
        
        response = await client.post("/tasks/search", json=search_data)
        response.raise_for_status()
        
        tasks = response.json()
        await ctx.info(f"Found {len(tasks)} matching task(s)")
        
        return {
            "count": len(tasks),
            "query": query,
            "tasks": tasks
        }


@mcp.tool
async def update_task(
    request: TaskUpdateRequest,
    ctx: Context
) -> Dict[str, Any]:
    """
    Update an existing task
    
    Update task properties like title, description, status, priority, or due date.
    """
    await ctx.info(f"Updating task {request.task_id}")
    
    async with get_http_client() as client:
        # Prepare update data
        update_data = {}
        if request.title is not None:
            update_data["title"] = request.title
        if request.description is not None:
            update_data["description"] = request.description
        if request.status is not None:
            update_data["status"] = request.status
        if request.priority is not None:
            update_data["priority"] = request.priority
        if request.due_date is not None:
            update_data["due_date"] = request.due_date
        
        # Update task
        response = await client.put(f"/tasks/{request.task_id}", json=update_data)
        response.raise_for_status()
        task = response.json()
        
        await ctx.info(f"Task updated successfully")
        return {
            "status": "updated",
            "task": task
        }


@mcp.tool
async def complete_task(
    task_id: str,
    ctx: Context
) -> Dict[str, Any]:
    """Mark a task as completed"""
    return await update_task(
        TaskUpdateRequest(task_id=task_id, status="completed"),
        ctx
    )


@mcp.tool
async def delete_task(
    task_id: str,
    ctx: Context
) -> Dict[str, Any]:
    """Delete (archive) a task"""
    await ctx.info(f"Deleting task {task_id}")
    
    async with get_http_client() as client:
        response = await client.delete(f"/tasks/{task_id}")
        response.raise_for_status()
        
        await ctx.info("Task deleted successfully")
        return {"status": "deleted", "task_id": task_id}


@mcp.tool
async def get_lists(ctx: Context) -> Dict[str, Any]:
    """Get all lists organized by workspace"""
    await ctx.info("Fetching lists...")
    
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
        
        await ctx.info(f"Found {len(lists)} list(s) across {len(by_workspace)} workspace(s)")
        
        return {
            "count": len(lists),
            "by_workspace": by_workspace
        }


# Resources
@mcp.resource("tasks://recent")
async def get_recent_tasks(ctx: Context) -> str:
    """Get recently modified tasks"""
    result = await list_tasks(limit=10, ctx=ctx)
    
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


# Prompts
@mcp.prompt
def daily_planning_prompt() -> str:
    """
    Prompt for daily task planning
    
    Helps organize the day by reviewing tasks and creating a plan.
    """
    return """Please help me plan my day by:

1. First, list all my tasks that are due today or overdue
2. Then, show my high-priority tasks that aren't due today
3. Suggest a reasonable order to tackle these tasks
4. Ask if I'd like to add any new tasks for today

Use the available tools to fetch and organize my tasks."""


if __name__ == "__main__":
    # Run the MCP server with STDIO transport for Claude Desktop
    mcp.run(transport="stdio")