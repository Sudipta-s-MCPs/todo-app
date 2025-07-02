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
        self.protocol_version = "2024-11-05"
        
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
            
            # Clean up
            await client.delete_task(task_id)
        else:
            test_results.append(("Create task", False, create_result.get("error", "Unknown error")))
        
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
        console.print("8. 🧪 Run quick test")
        console.print("9. 🚪 Exit")
        
        choice = Prompt.ask("Select an action", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"])
        
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
                # Run quick test
                await quick_test()
                
            elif choice == "9":
                # Exit
                console.print("👋 Goodbye!", style="green")
                break
                
        except Exception as e:
            console.print(f"❌ Error: {str(e)}", style="red")


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
        if len(sys.argv) > 1 and sys.argv[1] == "--quick":
            # Run quick test
            asyncio.run(quick_test())
        else:
            # Run interactive menu
            asyncio.run(interactive_menu())
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="green")
    except Exception as e:
        console.print(f"❌ Fatal error: {str(e)}", style="red")