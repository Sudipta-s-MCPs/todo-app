"""
MCP Server for Smart-ToDo application
Created: 2025-01-30 14:35:00 PST
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

# Initialize FastMCP server
mcp = FastMCP("Smart-ToDo MCP Server")

# Configuration from environment
API_KEY = os.environ.get("TODO_API_KEY", "")
USER_ID = os.environ.get("TODO_USER_ID", "")
DEVICE_ID = os.environ.get("TODO_DEVICE_ID", "")
API_ENDPOINT = os.environ.get("TODO_API_ENDPOINT", "http://localhost:8000/api/v1")
DEVICE_NAME = os.environ.get("TODO_DEVICE_NAME", "MCP Agent")

# HTTP client with authentication
headers = {
    "X-API-Key": API_KEY,
    "X-Device-ID": DEVICE_ID,
    "X-Device-Name": DEVICE_NAME,
    "X-Device-Type": "mcp_agent"
}


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


async def get_http_client() -> httpx.AsyncClient:
    """Get configured HTTP client"""
    return httpx.AsyncClient(
        base_url=API_ENDPOINT,
        headers=headers,
        timeout=30.0
    )


async def get_user_lists() -> List[Dict[str, Any]]:
    """Get all lists accessible to the user"""
    async with get_http_client() as client:
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
        lists = await get_user_lists()
        
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
                
                # Ask for confirmation
                confirm = await ctx.sample(
                    f"Potential duplicate tasks found:\\n{dup_info}\\n\\n"
                    f"Do you want to create the task anyway? (yes/no)"
                )
                
                if "yes" in confirm.text.lower():
                    # Force create
                    response = await client.post(
                        f"/lists/{target_list['id']}/tasks?force_create=true",
                        json=task_data
                    )
                else:
                    return {
                        "status": "cancelled",
                        "reason": "duplicate_found",
                        "duplicates": duplicates
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
            lists = await get_user_lists()
            
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
        
        # Handle duplicate detection on update
        if response.status_code == 409 and (request.title or request.description):
            conflict_data = response.json()
            duplicates = conflict_data.get("duplicates", [])
            
            if duplicates:
                await ctx.warning(f"Found {len(duplicates)} potential duplicate(s)")
                
                # Ask for confirmation
                confirm = await ctx.sample(
                    f"Updating this task would create a duplicate. Continue anyway? (yes/no)"
                )
                
                if "yes" in confirm.text.lower():
                    # Force update
                    response = await client.put(
                        f"/tasks/{request.task_id}?force_update=true",
                        json=update_data
                    )
                else:
                    return {
                        "status": "cancelled",
                        "reason": "would_create_duplicate"
                    }
        
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
async def create_list(
    name: str,
    workspace_name: Optional[str] = None,
    color: Optional[str] = "#000000",
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a new list in a workspace
    
    If no workspace is specified, uses the first available workspace.
    """
    await ctx.info(f"Creating list: {name}")
    
    async with get_http_client() as client:
        # Get workspaces
        workspaces_response = await client.get("/workspaces")
        workspaces_response.raise_for_status()
        workspaces = workspaces_response.json()
        
        if not workspaces:
            await ctx.error("No workspaces found. Please create a workspace first.")
            return {"error": "No workspaces available"}
        
        # Find target workspace
        target_workspace = workspaces[0]
        if workspace_name:
            for ws in workspaces:
                if ws['name'].lower() == workspace_name.lower():
                    target_workspace = ws
                    break
        
        # Create list
        list_data = {
            "name": name,
            "color": color
        }
        
        response = await client.post(
            f"/workspaces/{target_workspace['id']}/lists",
            json=list_data
        )
        response.raise_for_status()
        
        new_list = response.json()
        await ctx.info(f"List created successfully in workspace '{target_workspace['name']}'")
        
        return {
            "status": "created",
            "list": new_list,
            "workspace": target_workspace['name']
        }


@mcp.tool
async def get_lists(ctx: Context) -> Dict[str, Any]:
    """Get all lists organized by workspace"""
    await ctx.info("Fetching lists...")
    
    lists = await get_user_lists()
    
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


@mcp.tool
async def move_task(
    task_id: str,
    list_name: str,
    ctx: Context
) -> Dict[str, Any]:
    """Move a task to a different list"""
    await ctx.info(f"Moving task {task_id} to list '{list_name}'")
    
    # Find target list
    lists = await get_user_lists()
    target_list = None
    
    for lst in lists:
        if lst['name'].lower() == list_name.lower():
            target_list = lst
            break
    
    if not target_list:
        await ctx.error(f"List '{list_name}' not found")
        return {"error": f"List '{list_name}' not found"}
    
    # Update task with new list
    async with get_http_client() as client:
        response = await client.put(
            f"/tasks/{task_id}",
            json={"list_id": target_list['id']}
        )
        response.raise_for_status()
        
        await ctx.info(f"Task moved to '{list_name}' successfully")
        return {
            "status": "moved",
            "task_id": task_id,
            "new_list": list_name
        }


@mcp.tool
async def get_upcoming_tasks(
    days: int = 7,
    ctx: Context = None
) -> Dict[str, Any]:
    """Get tasks due in the next N days"""
    await ctx.info(f"Fetching tasks due in the next {days} days...")
    
    async with get_http_client() as client:
        # Calculate date range
        due_before = datetime.utcnow().replace(hour=23, minute=59, second=59)
        due_before = due_before.replace(day=due_before.day + days)
        
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
        
        await ctx.info(f"Found {len(tasks)} upcoming task(s)")
        
        return {
            "count": len(tasks),
            "days": days,
            "tasks": tasks
        }


@mcp.tool
async def smart_todo_manager(
    message: str,
    mode: str = "auto",
    conversation_context: Optional[List[Dict[str, str]]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    AI-powered assistant for task management with conversational capabilities
    
    This tool provides intelligent task management through natural conversation.
    It can understand context, suggest tasks, help with planning, and manage your todos.
    
    Modes:
    - auto: Let AI decide the best action based on your message
    - create_task: Force creation of a task from your message
    - chat: Get helpful responses without creating tasks
    - suggest: Get task suggestions without automatic creation
    
    Examples:
    - "I need to prepare for tomorrow's presentation"
    - "What tasks do I have due this week?"
    - "Help me plan my project timeline"
    - "Create a task to review the quarterly report"
    
    The AI will understand your intent and either:
    - Suggest a task for you to review and approve
    - Provide helpful information or guidance
    - Execute task queries and searches
    - Ask clarifying questions when needed
    """
    await ctx.info(f"Processing message with AI: {message[:50]}...")
    
    # Import AI service
    from app.services.ai_service import get_ai_service
    ai_service = get_ai_service()
    
    async with get_http_client() as client:
        # Get user's context
        workspaces_response = await client.get("/workspaces")
        workspaces_response.raise_for_status()
        workspaces = workspaces_response.json()
        
        lists = await get_user_lists()
        
        # Get user's recent tasks for context
        tasks_response = await client.post("/tasks/search", json={"limit": 20})
        tasks_response.raise_for_status()
        recent_tasks = tasks_response.json()
        
        # Build user context
        user_context = {
            "workspaces": [{"id": str(w["id"]), "name": w["name"]} for w in workspaces],
            "lists": [{"id": str(l["id"]), "name": l["name"], "workspace_id": str(l["workspace_id"]), "workspace_name": l["workspace_name"]} for l in lists],
            "task_count": len(recent_tasks)
        }
        
        # Convert conversation context if provided
        conv_history = []
        if conversation_context:
            for msg in conversation_context:
                conv_history.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Process with centralized AI
        ai_response = await ai_service.process_conversation(
            message=message,
            user_context=user_context,
            conversation_history=conv_history,
            mode="mcp",
            user_id=USER_ID
        )
        
        await ctx.info(f"AI intent: {ai_response.intent}, confidence: {ai_response.confidence}")
        
        # Handle different response types based on mode
        if mode == "chat" and ai_response.intent != "task_creation":
            # Pure chat mode - just return the response
            return {
                "status": "chat_response",
                "response": ai_response.response,
                "intent": ai_response.intent,
                "confidence": ai_response.confidence,
                "provider": ai_response.provider_used
            }
        
        elif mode == "suggest" or (mode == "auto" and ai_response.intent == "task_creation" and ai_response.task_details):
            # Suggest mode or auto mode with task creation intent
            task_details = ai_response.task_details
            
            # Validate workspace and list IDs
            workspace_name = None
            list_name = None
            
            if task_details.get("workspace_id"):
                ws = next((w for w in workspaces if str(w["id"]) == task_details["workspace_id"]), None)
                if ws:
                    workspace_name = ws["name"]
            
            if task_details.get("list_id"):
                lst = next((l for l in lists if str(l["id"]) == task_details["list_id"]), None)
                if lst:
                    list_name = lst["name"]
            
            # Return suggestion without creating
            return {
                "status": "task_suggested",
                "response": ai_response.response,
                "suggested_task": {
                    "title": task_details.get("title", "Untitled Task"),
                    "description": task_details.get("description"),
                    "workspace_id": task_details.get("workspace_id"),
                    "workspace_name": workspace_name,
                    "list_id": task_details.get("list_id"),
                    "list_name": list_name,
                    "priority": task_details.get("priority", "medium"),
                    "due_date": task_details.get("due_date")
                },
                "confidence": ai_response.confidence,
                "provider": ai_response.provider_used
            }
        
        elif mode == "create_task" or (ai_response.intent == "task_creation" and ai_response.task_details):
            # Force create mode or task creation intent
            task_details = ai_response.task_details
            
            # Find target list
            target_list = None
            if task_details.get("list_id"):
                target_list = next((l for l in lists if str(l["id"]) == task_details["list_id"]), None)
            
            if not target_list and lists:
                target_list = lists[0]  # Default to first list
            
            if not target_list:
                await ctx.error("No lists found. Please create a workspace and list first.")
                return {
                    "status": "error",
                    "error": "No lists available",
                    "response": "I couldn't find any lists to create the task in. Please create a workspace and list first."
                }
            
            # Prepare task data
            task_data = {
                "title": task_details.get("title", "Untitled Task"),
                "description": task_details.get("description"),
                "priority": task_details.get("priority", "medium"),
                "task_metadata": {
                    "created_via": "mcp_smart_todo_manager",
                    "ai_confidence": ai_response.confidence,
                    "original_message": message
                }
            }
            
            if task_details.get("due_date"):
                task_data["due_date"] = task_details["due_date"]
            
            # Create the task
            response = await client.post(
                f"/lists/{target_list['id']}/tasks",
                json=task_data
            )
            
            # Handle duplicate detection
            if response.status_code == 409:
                conflict_data = response.json()
                duplicates = conflict_data.get("duplicates", [])
                
                if duplicates:
                    # In MCP, we'll just inform about the duplicate
                    return {
                        "status": "duplicate_found",
                        "response": f"This task appears to be similar to an existing task: '{duplicates[0]['title']}'. You may want to update that task instead.",
                        "existing_task": duplicates[0],
                        "suggested_action": "update_existing"
                    }
            
            response.raise_for_status()
            created_task = response.json()
            
            await ctx.info(f"Task created successfully: {created_task['id']}")
            
            return {
                "status": "task_created",
                "response": f"I've created the task '{created_task['title']}' in {target_list['name']}.",
                "task": created_task,
                "list": target_list['name'],
                "workspace": target_list['workspace_name'],
                "confidence": ai_response.confidence,
                "provider": ai_response.provider_used
            }
        
        else:
            # General response - no task creation
            return {
                "status": "general_response",
                "response": ai_response.response,
                "intent": ai_response.intent,
                "confidence": ai_response.confidence,
                "provider": ai_response.provider_used
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


@mcp.resource("tasks://upcoming")
async def get_upcoming_tasks_resource(ctx: Context) -> str:
    """Get tasks due soon"""
    result = await get_upcoming_tasks(days=7, ctx=ctx)
    
    if not result.get('tasks'):
        return "No upcoming tasks in the next 7 days."
    
    lines = ["Upcoming tasks (next 7 days):\\n"]
    for task in result['tasks']:
        lines.append(f"- {task['title']}")
        if task.get('due_date'):
            lines.append(f"  Due: {task['due_date']}")
        lines.append(f"  Priority: {task['priority']}")
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


@mcp.prompt
def project_breakdown_prompt(project_name: str) -> str:
    """
    Prompt for breaking down a project into tasks
    
    Helps create a task list from a project description.
    """
    return f"""I need help breaking down a project: "{project_name}"

Please:
1. Ask me to describe the project goals and requirements
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
    # Run the MCP server with HTTP transport (recommended)
    mcp.run(transport="http", host="0.0.0.0", port=5485)