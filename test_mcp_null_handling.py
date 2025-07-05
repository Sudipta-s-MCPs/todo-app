#!/usr/bin/env python3
"""Test MCP server null handling"""

import httpx
import json
import os

# Base URL
base_url = "http://localhost:5485/mcp/"

# Common headers
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "X-API-Key": os.environ.get("TODO_API_KEY", "sk_todo_aaabbbccc")
}

print(f"Testing MCP server null handling at {base_url}")

# Test 1: Initialize session
print("\n1. Initializing session...")
response = httpx.post(
    base_url,
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0.0"}
        },
        "id": 1
    }
)
print(f"Status: {response.status_code}")

# Extract session ID
session_id = None
if response.text.startswith("event:"):
    lines = response.text.strip().split('\n')
    for line in lines:
        if line.startswith("data: "):
            data = json.loads(line[6:])
            print(f"Initialized: {data.get('result', {}).get('serverInfo', {})}")

# Get session ID from logs or headers
session_headers = headers.copy()
session_headers["mcp-session-id"] = "test-session"

# Test 2: List tasks with null parameters (simulating Claude's behavior)
print("\n2. Testing list_tasks with null parameters...")
response = httpx.post(
    base_url,
    headers=session_headers,
    json={
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
)
print(f"Status: {response.status_code}")
if response.text.startswith("event:"):
    lines = response.text.strip().split('\n')
    for line in lines:
        if line.startswith("data: "):
            data = json.loads(line[6:])
            if "result" in data:
                tools = data["result"].get("tools", [])
                print(f"Found {len(tools)} tools")
                print("First 3 tools:")
                for tool in tools[:3]:
                    print(f"  - {tool['name']}")

# Test 3: Call list_tasks with null values
print("\n3. Testing list_tasks with null values (simulating Claude)...")
response = httpx.post(
    base_url,
    headers=session_headers,
    json={
        "jsonrpc": "2.0",
        "method": "list_tasks",
        "params": {
            "workspace": None,  # This is what Claude sends
            "list_name": None,
            "status": None,
            "assigned_to": None,
            "limit": 10
        },
        "id": 3
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}...")

# Test 4: Call create_task with null optional fields
print("\n4. Testing create_task with null optional fields...")
response = httpx.post(
    base_url,
    headers=session_headers,
    json={
        "jsonrpc": "2.0",
        "method": "create_task",
        "params": {
            "title": "Test task with nulls",
            "description": None,  # Null instead of omitting
            "list_name": None,
            "priority": None,
            "due_date": None,
            "assigned_to": None
        },
        "id": 4
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}...")

# Test 5: Call update_task with null values
print("\n5. Testing update_task with null values...")
response = httpx.post(
    base_url,
    headers=session_headers,
    json={
        "jsonrpc": "2.0",
        "method": "update_task",
        "params": {
            "task_id": "test-id",
            "title": None,
            "description": None,
            "status": None,
            "priority": None,
            "due_date": None
        },
        "id": 5
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}...")

print("\n✅ MCP null handling test complete!")