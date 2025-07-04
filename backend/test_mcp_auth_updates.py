#!/usr/bin/env python3
"""
Test script to verify MCP auth method tracking
Created: 2025-07-04 16:15:00 PST
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
import os
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5482")  # Use localhost:8000 when inside container
ADMIN_EMAIL = "sudiptai26.889@gmail.com"
ADMIN_PASSWORD = "Whq3hUdZXY5qQ8"

async def main():
    async with httpx.AsyncClient() as client:
        # Login as admin
        print("1. Logging in as admin...")
        login_response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.text}")
            return
            
        auth_data = login_response.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"✓ Logged in successfully")
        
        # Get MCP agents list
        print("\n2. Fetching MCP agents...")
        agents_response = await client.get(
            f"{BASE_URL}/api/v1/admin/mcp/agents",
            headers=headers
        )
        
        if agents_response.status_code == 200:
            agents_data = agents_response.json()
            print(f"✓ Found {agents_data['total']} MCP agents")
            
            for agent in agents_data['agents']:
                print(f"\nMCP Agent: {agent['agent_name']}")
                print(f"  - ID: {agent['id']}")
                print(f"  - Auth Method: {agent.get('auth_method', 'N/A')}")
                print(f"  - Identifier: {agent['agent_identifier']}")
                print(f"  - User: {agent['user']['email']}")
                if agent.get('api_key'):
                    print(f"  - Linked API Key: {agent['api_key']['name']} (Active: {agent['api_key']['is_active']})")
        else:
            print(f"✗ Failed to fetch agents: {agents_response.text}")
        
        # Get API keys list
        print("\n3. Fetching API keys...")
        keys_response = await client.get(
            f"{BASE_URL}/api/v1/admin/api-keys",
            headers=headers
        )
        
        if keys_response.status_code == 200:
            keys_data = keys_response.json()
            print(f"✓ Found {keys_data['total']} API keys")
            
            mcp_keys = [k for k in keys_data['keys'] if k.get('mcp_agent')]
            print(f"  - {len(mcp_keys)} keys are linked to MCP agents")
            
            for key in mcp_keys:
                print(f"\nAPI Key: {key['name']}")
                print(f"  - MCP Agent: {key['mcp_agent']['name']}")
                print(f"  - MCP Identifier: {key['mcp_agent']['identifier']}")
        else:
            print(f"✗ Failed to fetch keys: {keys_response.text}")
        
        # Test creating a new MCP agent via admin panel
        print("\n4. Testing MCP agent registration...")
        register_response = await client.post(
            f"{BASE_URL}/api/v1/admin/mcp/register",
            headers=headers,
            json={
                "user_id": auth_data["user"]["id"],
                "agent_name": "Test MCP Client",
                "description": "Created by auth test script",
                "capabilities": ["task_management", "smart_todo_manager"]
            }
        )
        
        if register_response.status_code == 200:
            register_data = register_response.json()
            print(f"✓ Successfully registered MCP agent")
            print(f"  - Agent ID: {register_data['agent']['id']}")
            print(f"  - Auth Method: api_key (default)")
            print(f"  - Configuration available for: {', '.join(register_data['configurations'].keys())}")
        else:
            print(f"✗ Failed to register agent: {register_response.text}")

if __name__ == "__main__":
    asyncio.run(main())