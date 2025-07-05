#!/usr/bin/env python3
"""Test MCP server authentication"""

import httpx
import json
import os

# Get API key from environment
api_key = os.environ.get("TODO_API_KEY", "")

# Base URL
base_url = "http://localhost:5485/mcp/"

# Common headers
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

print(f"Testing MCP server at {base_url}")
print(f"Using API key: {api_key[:10]}..." if api_key else "No API key found")

# Test 1: Initialize without auth (should fail)
print("\n1. Testing initialize without auth...")
try:
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
    print(f"Response: {response.text[:200]}...")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Initialize with auth (should succeed)
print("\n2. Testing initialize with auth...")
auth_headers = headers.copy()
auth_headers["X-API-Key"] = api_key

try:
    response = httpx.post(
        base_url,
        headers=auth_headers,
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
    print(f"Response: {response.text[:200]}...")
    
    # Extract session ID from response headers
    session_id = response.headers.get("mcp-session-id", "")
    if session_id:
        print(f"Session ID: {session_id}")
    
    # Parse SSE response
    if response.text.startswith("event:"):
        lines = response.text.strip().split('\n')
        for line in lines:
            if line.startswith("data: "):
                data = json.loads(line[6:])
                print(f"Parsed response: {json.dumps(data, indent=2)}")
                
except Exception as e:
    print(f"Error: {e}")

# Test 3: List tools with auth
print("\n3. Testing list tools with auth...")
if 'session_id' in locals() and session_id:
    auth_headers["mcp-session-id"] = session_id

try:
    response = httpx.post(
        base_url,
        headers=auth_headers,
        json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
    )
    print(f"Status: {response.status_code}")
    
    # Parse SSE response
    if response.text.startswith("event:"):
        lines = response.text.strip().split('\n')
        for line in lines:
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if "result" in data:
                    tools = data["result"].get("tools", [])
                    print(f"Found {len(tools)} tools:")
                    for tool in tools[:3]:  # Show first 3 tools
                        print(f"  - {tool['name']}: {tool.get('description', '')[:60]}...")
                else:
                    print(f"Response: {json.dumps(data, indent=2)}")
                    
except Exception as e:
    print(f"Error: {e}")

print("\n✅ MCP server authentication test complete!")