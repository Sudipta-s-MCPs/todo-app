#!/usr/bin/env python3
"""
Test script for admin endpoints
Created: 2025-01-31 00:05:00 PST
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"


async def get_token(client: httpx.AsyncClient) -> str:
    """Login and get access token"""
    response = await client.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    if response.status_code != 200:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None
    
    data = response.json()
    return data["access_token"]


async def test_admin_endpoints():
    """Test admin endpoints"""
    async with httpx.AsyncClient() as client:
        # Get token
        token = await get_token(client)
        if not token:
            print("Failed to get token")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test user listing
        print("\n=== Testing GET /admin/users ===")
        response = await client.get(
            f"{BASE_URL}/admin/users",
            headers=headers,
            params={"page": 1, "page_size": 10}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total users: {data['total']}")
            print(f"Users on page: {len(data['items'])}")
            for user in data['items'][:3]:  # Show first 3
                print(f"  - {user['email']} ({user['name']})")
        else:
            print(f"Error: {response.text}")
        
        # Test API keys listing
        print("\n=== Testing GET /admin/api-keys ===")
        response = await client.get(
            f"{BASE_URL}/admin/api-keys",
            headers=headers,
            params={"page": 1, "page_size": 10}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total API keys: {data['total']}")
            print(f"Keys on page: {len(data['items'])}")
            for key in data['items'][:3]:  # Show first 3
                print(f"  - {key['name']} (User: {key['user_email']})")
        else:
            print(f"Error: {response.text}")
        
        # Test MCP agents listing
        print("\n=== Testing GET /admin/mcp/agents ===")
        response = await client.get(
            f"{BASE_URL}/admin/mcp/agents",
            headers=headers,
            params={"page": 1, "page_size": 10}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total MCP agents: {data['total']}")
            print(f"Agents on page: {len(data['items'])}")
            for agent in data['items'][:3]:  # Show first 3
                print(f"  - {agent['name']} (User: {agent['user_email']})")
        else:
            print(f"Error: {response.text}")


if __name__ == "__main__":
    print(f"Testing admin endpoints at {datetime.now().strftime('%Y-%m-%d %H:%M:%S PST')}")
    asyncio.run(test_admin_endpoints())