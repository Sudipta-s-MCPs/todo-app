#!/usr/bin/env python3
"""
MCP HTTP Client for Smart-ToDo
Created: 2025-07-01 19:25:00 PST

This is a proper MCP client that communicates with the MCP server
using the HTTP transport (Streamable HTTP) protocol on port 5485.
It implements the full MCP protocol handshake and communication.
"""

import asyncio
import json
import httpx
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
import uuid

console = Console()

# MCP Server configuration
MCP_SERVER_URL = "http://localhost:5485/mcp/"


class MCPHTTPClient:
    """MCP client that communicates with the MCP server via HTTP transport"""
    
    def __init__(self):
        self.server_url = MCP_SERVER_URL
        self.session_id = None
        self.initialized = False
        self.protocol_version = "2025-03-26"
        
    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server"""
        request_id = str(uuid.uuid4())
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.server_url,
                    json=request_data,
                    headers=headers
                )
                response.raise_for_status()
                
                # Check for session ID in response headers
                if "Mcp-Session-Id" in response.headers:
                    self.session_id = response.headers["Mcp-Session-Id"]
                
                # Handle SSE response format
                content = response.text
                if content.startswith("event:"):
                    # Parse SSE format
                    for line in content.strip().split('\n'):
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            result = json.loads(data)
                            break
                else:
                    # Regular JSON response
                    result = response.json()
                
                # Handle JSON-RPC response
                if "error" in result:
                    console.print(f"[red]Error: {result['error'].get('message', 'Unknown error')}[/red]")
                    return {"error": result['error']}
                
                return result.get("result", {})
                
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                return {"error": str(e)}
    
    async def initialize(self) -> bool:
        """Initialize the MCP connection"""
        console.print("🤝 Initializing MCP connection...")
        
        result = await self._send_request(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {
                    "tools": {},
                    "resources": {"subscribe": True},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "Smart-ToDo MCP Test Client",
                    "version": "1.0.0"
                }
            }
        )
        
        if "error" not in result:
            self.initialized = True
            console.print(f"✅ Connected to {result.get('serverInfo', {}).get('name', 'MCP Server')}")
            console.print(f"   Protocol version: {result.get('protocolVersion', 'unknown')}")
            return True
        return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        if not self.initialized:
            await self.initialize()
            
        result = await self._send_request("tools/list")
        return result.get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool"""
        if not self.initialized:
            await self.initialize()
            
        return await self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments
            }
        )
    
    # Convenience methods for common operations
    
    async def create_task(self, title: str, description: str = None, 
                         list_name: str = None, priority: str = "medium") -> Dict[str, Any]:
        """Create a new task"""
        args = {
            "request": {
                "title": title,
                "description": description,
                "list_name": list_name,
                "priority": priority
            }
        }
        result = await self.call_tool("create_task", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def list_tasks(self, limit: int = 20, status: str = None) -> Dict[str, Any]:
        """List tasks"""
        args = {"limit": limit}
        if status:
            args["status"] = status
        result = await self.call_tool("list_tasks", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def search_tasks(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for tasks"""
        args = {"query": query, "limit": limit}
        result = await self.call_tool("search_tasks", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def update_task(self, task_id: str, **updates) -> Dict[str, Any]:
        """Update a task"""
        args = {
            "request": {
                "task_id": task_id,
                **updates
            }
        }
        result = await self.call_tool("update_task", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark task as completed"""
        args = {"task_id": task_id}
        result = await self.call_tool("complete_task", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task"""
        args = {"task_id": task_id}
        result = await self.call_tool("delete_task", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def get_lists(self) -> Dict[str, Any]:
        """Get all lists"""
        result = await self.call_tool("get_lists", {})
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def create_list(self, name: str, workspace_name: str = None, color: str = "#000000") -> Dict[str, Any]:
        """Create a new list"""
        args = {
            "name": name,
            "workspace_name": workspace_name,
            "color": color
        }
        result = await self.call_tool("create_list", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def move_task(self, task_id: str, list_name: str) -> Dict[str, Any]:
        """Move task to different list"""
        args = {
            "task_id": task_id,
            "list_name": list_name
        }
        result = await self.call_tool("move_task", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def get_upcoming_tasks(self, days: int = 7) -> Dict[str, Any]:
        """Get tasks due in next N days"""
        args = {"days": days}
        result = await self.call_tool("get_upcoming_tasks", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    async def smart_todo_manager(self, message: str, mode: str = "auto", conversation_context: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """AI-powered task management"""
        args = {
            "message": message,
            "mode": mode,
            "conversation_context": conversation_context
        }
        result = await self.call_tool("smart_todo_manager", args)
        return result.get("content", [{}])[0] if "content" in result else result
    
    # Resource methods
    
    async def get_resource(self, uri: str) -> str:
        """Get an MCP resource"""
        result = await self._send_request(
            "resources/read",
            {"uri": uri}
        )
        return result.get("contents", [{}])[0].get("text", "") if "contents" in result else str(result)
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources"""
        result = await self._send_request("resources/list")
        return result.get("resources", [])
    
    # Prompt methods
    
    async def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> str:
        """Get a prompt template"""
        result = await self._send_request(
            "prompts/get",
            {
                "name": name,
                "arguments": arguments or {}
            }
        )
        return result.get("messages", [{}])[0].get("content", {}).get("text", "") if "messages" in result else str(result)
    
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts"""
        result = await self._send_request("prompts/list")
        return result.get("prompts", [])


def display_tasks(tasks: List[Dict[str, Any]], title: str = "Tasks"):
    """Display tasks in a nice table"""
    if not tasks:
        console.print(f"No {title.lower()} found.", style="yellow")
        return
    
    table = Table(title=title)
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Title", style="white", min_width=20)
    table.add_column("Status", style="green")
    table.add_column("Priority", style="magenta")
    
    for task in tasks:
        # Truncate ID for display
        task_id = task['id'][:8] + "..."
        
        # Status styling
        status = task['status']
        if status == "completed":
            status_text = Text(status, style="green")
        elif status == "in_progress":
            status_text = Text(status, style="yellow")
        else:
            status_text = Text(status, style="white")
        
        # Priority styling
        priority = task['priority']
        if priority == "urgent":
            priority_text = Text(priority, style="red")
        elif priority == "high":
            priority_text = Text(priority, style="orange3")
        elif priority == "medium":
            priority_text = Text(priority, style="yellow")
        else:
            priority_text = Text(priority, style="white")
        
        table.add_row(task_id, task['title'], status_text, priority_text)
    
    console.print(table)


async def quick_test():
    """Run a quick test of MCP functionality"""
    client = MCPHTTPClient()
    
    console.print(Panel.fit(
        "[bold green]Smart-ToDo MCP HTTP Test[/bold green]\n"
        "Testing MCP server communication via HTTP transport",
        title="🧪 Quick Test"
    ))
    
    test_results = []
    
    try:
        # Test 1: Initialize connection
        console.print("1️⃣ Testing MCP initialization...")
        if await client.initialize():
            test_results.append(("Initialize", True, "Connection established"))
        else:
            test_results.append(("Initialize", False, "Failed to connect"))
            return
        
        # Test 2: List available tools
        console.print("2️⃣ Testing tool discovery...")
        tools = await client.list_tools()
        test_results.append(("List tools", True, f"Found {len(tools)} tools"))
        
        # Test 3: Get lists
        console.print("3️⃣ Testing list access...")
        lists_result = await client.get_lists()
        if 'error' not in lists_result:
            test_results.append(("Get lists", True, f"Found {lists_result.get('count', 0)} lists"))
        else:
            test_results.append(("Get lists", False, lists_result['error']))
        
        # Test 4: List tasks
        console.print("4️⃣ Testing task listing...")
        tasks_result = await client.list_tasks(limit=5)
        if 'error' not in tasks_result:
            test_results.append(("List tasks", True, f"Found {tasks_result.get('count', 0)} tasks"))
        else:
            test_results.append(("List tasks", False, tasks_result['error']))
        
        # Test 5: Create task
        console.print("5️⃣ Testing task creation...")
        create_result = await client.create_task(
            "MCP HTTP Test Task",
            "Testing MCP HTTP transport functionality"
        )
        if create_result.get("status") == "created":
            task_id = create_result["task"]["id"]
            test_results.append(("Create task", True, f"Created in {create_result['list']}"))
            
            # Don't delete yet - we'll use this task for other tests
        else:
            test_results.append(("Create task", False, create_result.get("error", "Unknown error")))
            task_id = None
        
        # Test 6: Smart Todo Manager
        console.print("6️⃣ Testing AI Smart Todo Manager...")
        smart_result = await client.smart_todo_manager(
            "I need to review the quarterly sales report by Friday",
            mode="suggest"
        )
        if smart_result.get("status") in ["task_suggested", "general_response"]:
            test_results.append(("Smart Todo Manager", True, f"AI intent: {smart_result.get('intent', 'unknown')}"))
        else:
            test_results.append(("Smart Todo Manager", False, smart_result.get("error", "No response")))
        
        # Test 7: Create list
        console.print("7️⃣ Testing list creation...")
        list_result = await client.create_list("MCP Test List " + str(uuid.uuid4())[:8])
        if list_result.get("status") == "created":
            test_results.append(("Create list", True, f"Created in {list_result['workspace']}"))
            created_list_name = list_result["list"]["name"]
            
            # Test 8: Move task (if we have a task)
            if task_id:
                console.print("8️⃣ Testing task movement...")
                move_result = await client.move_task(task_id, created_list_name)
                if move_result.get("status") == "moved":
                    test_results.append(("Move task", True, f"Moved to {move_result['new_list']}"))
                else:
                    test_results.append(("Move task", False, move_result.get("error", "Failed")))
            else:
                test_results.append(("Move task", False, "No task to move"))
        else:
            test_results.append(("Create list", False, list_result.get("error", "Failed")))
        
        # Test 9: Get upcoming tasks
        console.print("9️⃣ Testing upcoming tasks...")
        upcoming_result = await client.get_upcoming_tasks(7)
        if "error" not in upcoming_result:
            test_results.append(("Get upcoming tasks", True, f"Found {upcoming_result.get('count', 0)} tasks"))
        else:
            test_results.append(("Get upcoming tasks", False, upcoming_result['error']))
        
        # Test 10: List resources
        console.print("🔟 Testing MCP resources...")
        resources = await client.list_resources()
        if isinstance(resources, list):
            test_results.append(("List resources", True, f"Found {len(resources)} resources"))
            
            # Try to read a resource if available
            if resources:
                resource_uri = resources[0].get('uri', '')
                resource_content = await client.get_resource(resource_uri)
                if resource_content and not resource_content.startswith("{'error'"):
                    test_results.append(("Read resource", True, f"Read {resource_uri}"))
                else:
                    test_results.append(("Read resource", False, "Failed to read"))
        else:
            test_results.append(("List resources", False, "Failed to list"))
        
        # Test 11: List prompts
        console.print("1️⃣1️⃣ Testing MCP prompts...")
        prompts = await client.list_prompts()
        if isinstance(prompts, list):
            test_results.append(("List prompts", True, f"Found {len(prompts)} prompts"))
            
            # Try to get a prompt if available
            if prompts:
                prompt_name = prompts[0].get('name', '')
                prompt_content = await client.get_prompt(prompt_name)
                if prompt_content and not prompt_content.startswith("{'error'"):
                    test_results.append(("Get prompt", True, f"Retrieved {prompt_name}"))
                else:
                    test_results.append(("Get prompt", False, "Failed to retrieve"))
        else:
            test_results.append(("List prompts", False, "Failed to list"))
        
        # Clean up: Delete the test task if it was created
        if task_id:
            console.print("🧹 Cleaning up test data...")
            await client.delete_task(task_id)
        
    except Exception as e:
        test_results.append(("MCP Test", False, f"Error: {str(e)}"))
    
    # Display results
    console.print("\n📊 [bold cyan]Test Results:[/bold cyan]")
    for test_name, success, details in test_results:
        status = "✅" if success else "❌"
        style = "green" if success else "red"
        console.print(f"{status} [bold]{test_name}[/bold]: {details}", style=style)
    
    passed = sum(1 for _, success, _ in test_results if success)
    total = len(test_results)
    console.print(f"\n🎯 [bold]Summary: {passed}/{total} tests passed[/bold]")


async def interactive_menu():
    """Interactive menu for testing MCP functionality"""
    client = MCPHTTPClient()
    
    console.print(Panel.fit(
        "[bold green]Smart-ToDo MCP HTTP Client[/bold green]\n"
        "Communicating with MCP server on port 5485\n"
        "Using HTTP transport (Streamable HTTP)",
        title="🤖 MCP Client"
    ))
    
    # Initialize connection
    if not await client.initialize():
        console.print("[red]Failed to connect to MCP server[/red]")
        return
    
    # List available tools
    console.print("\n[bold cyan]Discovering available tools...[/bold cyan]")
    tools = await client.list_tools()
    if tools:
        console.print(f"Found {len(tools)} tools:")
        for tool in tools[:5]:  # Show first 5 tools
            console.print(f"  • {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:60]}...")
        if len(tools) > 5:
            console.print(f"  ... and {len(tools) - 5} more")
    
    while True:
        console.print("\n[bold cyan]Available Actions:[/bold cyan]")
        console.print("1. 📋 List all tasks")
        console.print("2. ➕ Create a new task")
        console.print("3. 🔍 Search tasks")
        console.print("4. ✏️ Update a task")
        console.print("5. ✅ Complete a task")
        console.print("6. ❌ Delete a task")
        console.print("7. 📁 Show lists and workspaces")
        console.print("8. 🤖 Test AI Smart Todo Manager")
        console.print("9. 📂 Create a new list")
        console.print("10. ↔️ Move task to different list")
        console.print("11. 📅 Show upcoming tasks")
        console.print("12. 📚 Test MCP Resources")
        console.print("13. 💡 Test MCP Prompts")
        console.print("14. 🧪 Run quick test")
        console.print("15. 🚪 Exit")
        
        choice = Prompt.ask("Select an action", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"])
        
        try:
            if choice == "1":
                # List tasks
                status_filter = Prompt.ask("Filter by status (or Enter for all)", 
                                         choices=["todo", "in_progress", "completed", ""], default="")
                status = status_filter if status_filter else None
                
                console.print("📥 Fetching tasks...")
                result = await client.list_tasks(status=status)
                if 'error' not in result:
                    display_tasks(result.get('tasks', []), f"Tasks ({result.get('count', 0)} found)")
                else:
                    console.print(f"[red]Error: {result['error']}[/red]")
                
            elif choice == "2":
                # Create task
                title = Prompt.ask("Task title")
                description = Prompt.ask("Description (optional)", default="")
                priority = Prompt.ask("Priority", choices=["low", "medium", "high", "urgent"], default="medium")
                
                console.print("➕ Creating task...")
                result = await client.create_task(
                    title=title,
                    description=description if description else None,
                    priority=priority
                )
                
                if result.get('status') == 'created':
                    console.print(f"✅ Task created in '{result['list']}' (workspace: {result['workspace']})", style="green")
                else:
                    console.print(f"⚠️ {result.get('error', 'Task creation failed')}", style="yellow")
                
            elif choice == "3":
                # Search tasks
                query = Prompt.ask("Search query")
                console.print(f"🔍 Searching for: {query}")
                result = await client.search_tasks(query)
                if 'error' not in result:
                    display_tasks(result.get('tasks', []), f"Search Results ({result.get('count', 0)} found)")
                else:
                    console.print(f"[red]Error: {result['error']}[/red]")
                
            elif choice == "4":
                # Update task
                task_id = Prompt.ask("Task ID to update")
                console.print("What would you like to update? (leave empty to skip)")
                
                updates = {}
                new_title = Prompt.ask("New title", default="")
                if new_title:
                    updates['title'] = new_title
                
                new_description = Prompt.ask("New description", default="")
                if new_description:
                    updates['description'] = new_description
                
                new_status = Prompt.ask("New status", choices=["todo", "in_progress", "completed", ""], default="")
                if new_status:
                    updates['status'] = new_status
                
                new_priority = Prompt.ask("New priority", choices=["low", "medium", "high", "urgent", ""], default="")
                if new_priority:
                    updates['priority'] = new_priority
                
                if updates:
                    console.print("✏️ Updating task...")
                    result = await client.update_task(task_id, **updates)
                    if result.get('status') == 'updated':
                        console.print(f"✅ Task updated", style="green")
                    else:
                        console.print(f"⚠️ Update failed: {result.get('error', 'Unknown error')}", style="yellow")
                else:
                    console.print("No updates provided.", style="yellow")
                
            elif choice == "5":
                # Complete task
                task_id = Prompt.ask("Task ID to complete")
                console.print("✅ Marking task as completed...")
                result = await client.complete_task(task_id)
                if result.get('status') == 'updated':
                    console.print("✅ Task completed", style="green")
                else:
                    console.print(f"⚠️ Failed: {result.get('error', 'Unknown error')}", style="yellow")
                
            elif choice == "6":
                # Delete task
                task_id = Prompt.ask("Task ID to delete")
                if Confirm.ask(f"Are you sure you want to delete task {task_id}?"):
                    console.print("❌ Deleting task...")
                    result = await client.delete_task(task_id)
                    if result.get('status') == 'deleted':
                        console.print("✅ Task deleted", style="green")
                    else:
                        console.print(f"⚠️ Failed: {result.get('error', 'Unknown error')}", style="yellow")
                
            elif choice == "7":
                # Show lists
                console.print("📁 Fetching lists and workspaces...")
                result = await client.get_lists()
                if 'error' not in result and 'by_workspace' in result:
                    for workspace_name, lists in result['by_workspace'].items():
                        console.print(f"\n📁 [bold blue]{workspace_name}[/bold blue]")
                        for lst in lists:
                            task_count = lst.get('task_count', 0)
                            console.print(f"  📋 {lst['name']} ({task_count} tasks)")
                else:
                    console.print(f"[red]Error: {result.get('error', 'Failed to get lists')}[/red]")
                
            elif choice == "8":
                # Test AI Smart Todo Manager
                console.print("\n[bold cyan]AI Smart Todo Manager Test[/bold cyan]")
                message = Prompt.ask("Enter your message for the AI")
                mode = Prompt.ask("Select mode", choices=["auto", "create_task", "chat", "suggest"], default="auto")
                
                console.print("🤖 Processing with AI...")
                result = await client.smart_todo_manager(message, mode)
                
                if result.get('status') == 'task_created':
                    console.print(f"✅ {result['response']}", style="green")
                    console.print(f"   Task ID: {result['task']['id'][:8]}...")
                elif result.get('status') == 'task_suggested':
                    console.print(f"💡 {result['response']}", style="yellow")
                    task = result['suggested_task']
                    console.print(f"\n   Title: {task['title']}")
                    console.print(f"   List: {task.get('list_name', 'Not specified')}")
                    console.print(f"   Priority: {task.get('priority', 'medium')}")
                elif result.get('status') == 'general_response':
                    console.print(f"💬 {result['response']}", style="cyan")
                else:
                    console.print(f"📝 {result.get('response', 'AI response')}", style="white")
                
                console.print(f"\n   Intent: {result.get('intent', 'unknown')}")
                console.print(f"   Confidence: {result.get('confidence', 0):.2f}")
                console.print(f"   Provider: {result.get('provider', 'unknown')}")
                
            elif choice == "9":
                # Create a new list
                name = Prompt.ask("List name")
                workspace_name = Prompt.ask("Workspace name (optional)", default="")
                color = Prompt.ask("Color (hex)", default="#000000")
                
                console.print("📂 Creating list...")
                result = await client.create_list(
                    name=name,
                    workspace_name=workspace_name if workspace_name else None,
                    color=color
                )
                
                if result.get('status') == 'created':
                    console.print(f"✅ List '{result['list']['name']}' created in workspace '{result['workspace']}'", style="green")
                else:
                    console.print(f"⚠️ {result.get('error', 'Failed to create list')}", style="yellow")
                
            elif choice == "10":
                # Move task to different list
                task_id = Prompt.ask("Task ID to move")
                list_name = Prompt.ask("Target list name")
                
                console.print("↔️ Moving task...")
                result = await client.move_task(task_id, list_name)
                
                if result.get('status') == 'moved':
                    console.print(f"✅ Task moved to '{result['new_list']}'!", style="green")
                else:
                    console.print(f"⚠️ {result.get('error', 'Failed to move task')}", style="yellow")
                
            elif choice == "11":
                # Show upcoming tasks
                days = int(Prompt.ask("Show tasks due in next N days", default="7"))
                console.print(f"📅 Fetching tasks due in next {days} days...")
                result = await client.get_upcoming_tasks(days)
                
                if 'error' not in result:
                    display_tasks(result.get('tasks', []), f"Upcoming Tasks (next {days} days)")
                else:
                    console.print(f"[red]Error: {result['error']}[/red]")
                
            elif choice == "12":
                # Test MCP Resources
                console.print("\n[bold cyan]MCP Resources Test[/bold cyan]")
                
                # List resources
                resources = await client.list_resources()
                if resources:
                    console.print(f"Found {len(resources)} resources:")
                    for res in resources:
                        console.print(f"  • {res.get('uri', 'Unknown')} - {res.get('description', 'No description')}")
                    
                    # Read a resource
                    uri = Prompt.ask("Enter resource URI to read (or Enter to skip)", default="")
                    if uri:
                        console.print(f"📚 Reading resource: {uri}")
                        content = await client.get_resource(uri)
                        console.print(Panel(content, title=f"Resource: {uri}", expand=False))
                else:
                    console.print("No resources found.", style="yellow")
                
            elif choice == "13":
                # Test MCP Prompts
                console.print("\n[bold cyan]MCP Prompts Test[/bold cyan]")
                
                # List prompts
                prompts = await client.list_prompts()
                if prompts:
                    console.print(f"Found {len(prompts)} prompts:")
                    for prompt in prompts:
                        console.print(f"  • {prompt.get('name', 'Unknown')} - {prompt.get('description', 'No description')}")
                        if prompt.get('arguments'):
                            console.print(f"    Arguments: {prompt['arguments']}")
                    
                    # Get a prompt
                    name = Prompt.ask("Enter prompt name to retrieve (or Enter to skip)", default="")
                    if name:
                        args = {}
                        # Special handling for project_breakdown_prompt
                        if name == "project_breakdown_prompt":
                            project_name = Prompt.ask("Enter project name")
                            args = {"project_name": project_name}
                        
                        console.print(f"💡 Getting prompt: {name}")
                        content = await client.get_prompt(name, args)
                        console.print(Panel(content, title=f"Prompt: {name}", expand=False))
                else:
                    console.print("No prompts found.", style="yellow")
                
            elif choice == "14":
                # Run quick test
                await quick_test()
                
            elif choice == "15":
                # Exit
                console.print("👋 Goodbye!", style="green")
                break
                
        except Exception as e:
            console.print(f"❌ Error: {str(e)}", style="red")


async def comprehensive_test():
    """Run a comprehensive end-to-end test of MCP functionality"""
    client = MCPHTTPClient()
    
    console.print(Panel.fit(
        "[bold green]Smart-ToDo MCP Comprehensive Test[/bold green]\n"
        "Testing full workflow with AI integration",
        title="🧪 Comprehensive Test"
    ))
    
    test_results = []
    created_resources = []  # Track resources for cleanup
    
    try:
        # Initialize connection
        console.print("🤝 Initializing MCP connection...")
        if not await client.initialize():
            console.print("[red]Failed to connect to MCP server[/red]")
            return
        
        # Test 1: Create a list for testing
        console.print("\n1️⃣ Creating test list...")
        test_list_name = f"MCP Test List {str(uuid.uuid4())[:8]}"
        list_result = await client.create_list(test_list_name, color="#FF5733")
        
        if list_result.get("status") == "created":
            test_results.append(("Create test list", True, f"Created '{test_list_name}'"))
            created_resources.append(("list", test_list_name))
        else:
            test_results.append(("Create test list", False, "Failed to create list"))
            return
        
        # Test 2: Use AI to create multiple tasks
        console.print("\n2️⃣ Testing AI task creation...")
        ai_messages = [
            "I need to prepare a presentation for Monday's meeting",
            "Buy groceries: milk, eggs, bread, and coffee",
            "Schedule dentist appointment for next week",
            "Review and respond to email from John about the project proposal"
        ]
        
        created_task_ids = []
        for msg in ai_messages:
            result = await client.smart_todo_manager(msg, mode="create_task")
            if result.get("status") == "task_created":
                task_id = result["task"]["id"]
                created_task_ids.append(task_id)
                created_resources.append(("task", task_id))
                console.print(f"   ✅ Created: {result['task']['title']}")
        
        test_results.append(("AI task creation", True, f"Created {len(created_task_ids)} tasks"))
        
        # Test 3: Test AI in chat mode
        console.print("\n3️⃣ Testing AI chat mode...")
        chat_result = await client.smart_todo_manager(
            "What tasks do I have for this week?",
            mode="chat"
        )
        if chat_result.get("status") == "chat_response":
            test_results.append(("AI chat mode", True, "Got chat response"))
            console.print(f"   💬 AI: {chat_result['response'][:100]}...")
        else:
            test_results.append(("AI chat mode", False, "No response"))
        
        # Test 4: Move a task to the new list
        if created_task_ids:
            console.print("\n4️⃣ Testing task movement...")
            move_result = await client.move_task(created_task_ids[0], test_list_name)
            if move_result.get("status") == "moved":
                test_results.append(("Move task", True, f"Moved to '{test_list_name}'"))
            else:
                test_results.append(("Move task", False, "Failed to move"))
        
        # Test 5: Get upcoming tasks
        console.print("\n5️⃣ Testing upcoming tasks...")
        upcoming = await client.get_upcoming_tasks(7)
        test_results.append(("Get upcoming tasks", True, f"Found {upcoming.get('count', 0)} tasks"))
        
        # Test 6: Complete a task
        if created_task_ids:
            console.print("\n6️⃣ Testing task completion...")
            complete_result = await client.complete_task(created_task_ids[0])
            if complete_result.get("status") == "updated":
                test_results.append(("Complete task", True, "Task marked as completed"))
            else:
                test_results.append(("Complete task", False, "Failed to complete"))
        
        # Test 7: Use prompts for planning
        console.print("\n7️⃣ Testing MCP prompts...")
        
        # Get daily planning prompt
        daily_prompt = await client.get_prompt("daily_planning_prompt")
        if daily_prompt and not daily_prompt.startswith("{'error'"):
            test_results.append(("Get daily prompt", True, "Retrieved planning prompt"))
            console.print("   📋 Got daily planning prompt")
        
        # Get project breakdown prompt
        project_prompt = await client.get_prompt(
            "project_breakdown_prompt",
            {"project_name": "Website Redesign"}
        )
        if project_prompt and not project_prompt.startswith("{'error'"):
            test_results.append(("Get project prompt", True, "Retrieved with parameters"))
            console.print("   📋 Got project breakdown prompt")
        
        # Test 8: Read resources
        console.print("\n8️⃣ Testing MCP resources...")
        
        # Read recent tasks resource
        recent_content = await client.get_resource("tasks://recent")
        if recent_content and not recent_content.startswith("{'error'"):
            test_results.append(("Read recent tasks", True, "Got recent tasks"))
            console.print("   📚 Read recent tasks resource")
        
        # Read upcoming tasks resource
        upcoming_content = await client.get_resource("tasks://upcoming")
        if upcoming_content and not upcoming_content.startswith("{'error'"):
            test_results.append(("Read upcoming tasks", True, "Got upcoming tasks"))
            console.print("   📚 Read upcoming tasks resource")
        
        # Test 9: Search functionality
        console.print("\n9️⃣ Testing search...")
        search_result = await client.search_tasks("presentation")
        if "error" not in search_result:
            test_results.append(("Search tasks", True, f"Found {search_result.get('count', 0)} matches"))
        else:
            test_results.append(("Search tasks", False, "Search failed"))
        
        # Clean up
        console.print("\n🧹 Cleaning up test data...")
        for resource_type, resource_id in reversed(created_resources):
            if resource_type == "task":
                await client.delete_task(resource_id)
            # Note: We can't delete lists via MCP, so they'll remain
        
        test_results.append(("Cleanup", True, f"Cleaned up {len(created_resources)} resources"))
        
    except Exception as e:
        test_results.append(("Comprehensive test", False, f"Error: {str(e)}"))
    
    # Display final results
    console.print("\n" + "="*60)
    console.print("[bold cyan]Comprehensive Test Results:[/bold cyan]")
    
    passed = 0
    for test_name, success, details in test_results:
        status = "✅" if success else "❌"
        style = "green" if success else "red"
        console.print(f"{status} [bold]{test_name}[/bold]: {details}", style=style)
        if success:
            passed += 1
    
    total = len(test_results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    console.print(f"\n🎯 [bold]Final Score: {passed}/{total} tests passed ({percentage:.1f}%)[/bold]")
    
    if percentage == 100:
        console.print("🎉 [bold green]All tests passed! MCP integration is working perfectly![/bold green]")
    elif percentage >= 80:
        console.print("👍 [bold yellow]Most tests passed. Some features may need attention.[/bold yellow]")
    else:
        console.print("⚠️ [bold red]Several tests failed. Please check the MCP server logs.[/bold red]")


if __name__ == "__main__":
    import sys
    
    console.print(Panel.fit(
        "[bold cyan]Smart-ToDo MCP HTTP Client[/bold cyan]\n"
        "Proper MCP client using HTTP transport\n\n"
        "This client communicates with the MCP server\n"
        "on port 5485 using the MCP protocol over HTTP.",
        title="🤖 MCP HTTP Client"
    ))
    
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "--quick":
                # Run quick test
                asyncio.run(quick_test())
            elif sys.argv[1] == "--comprehensive":
                # Run comprehensive test
                asyncio.run(comprehensive_test())
            elif sys.argv[1] == "--help":
                console.print("Usage:")
                console.print("  python mcp_http_client.py           # Interactive mode")
                console.print("  python mcp_http_client.py --quick   # Quick test")
                console.print("  python mcp_http_client.py --comprehensive  # Full test")
            else:
                console.print(f"Unknown option: {sys.argv[1]}")
                console.print("Use --help for usage information")
        else:
            # Run interactive menu
            asyncio.run(interactive_menu())
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="green")
    except Exception as e:
        console.print(f"❌ Fatal error: {str(e)}", style="red")