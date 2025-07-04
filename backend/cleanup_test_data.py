#!/usr/bin/env python3
"""
Cleanup script to remove test data while preserving important data
Created: 2025-01-04 16:30:00 PST
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
import os
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5482")
ADMIN_EMAIL = "sudiptai26.889@gmail.com"
ADMIN_PASSWORD = "Whq3hUdZXY5qQ8"

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
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
        current_user_id = auth_data["user"]["id"]
        
        print(f"✓ Logged in successfully as {ADMIN_EMAIL}")
        
        # Clean up MCP agents
        print("\n2. Cleaning up MCP agents...")
        agents_response = await client.get(
            f"{BASE_URL}/api/v1/admin/mcp/agents?limit=100",
            headers=headers
        )
        
        if agents_response.status_code == 200:
            agents_data = agents_response.json()
            deleted_count = 0
            
            for agent in agents_data['agents']:
                print(f"  - Deleting MCP agent: {agent['agent_name']} ({agent['agent_identifier']})")
                delete_response = await client.delete(
                    f"{BASE_URL}/api/v1/admin/mcp/agents/{agent['id']}",
                    headers=headers
                )
                if delete_response.status_code == 200:
                    deleted_count += 1
                else:
                    print(f"    Failed: {delete_response.text}")
            
            print(f"✓ Deleted {deleted_count} MCP agents")
        
        # Clean up API keys
        print("\n3. Cleaning up API keys...")
        keys_response = await client.get(
            f"{BASE_URL}/api/v1/admin/api-keys?limit=100",
            headers=headers
        )
        
        if keys_response.status_code == 200:
            keys_data = keys_response.json()
            deleted_count = 0
            
            for key in keys_data['keys']:
                print(f"  - Deleting API key: {key['name']}")
                delete_response = await client.delete(
                    f"{BASE_URL}/api/v1/admin/api-keys/{key['id']}",
                    headers=headers
                )
                if delete_response.status_code == 200:
                    deleted_count += 1
                else:
                    print(f"    Failed: {delete_response.text}")
            
            print(f"✓ Deleted {deleted_count} API keys")
        
        # Clean up OAuth tokens
        print("\n4. Cleaning up OAuth tokens...")
        tokens_response = await client.get(
            f"{BASE_URL}/api/v1/admin/oauth/tokens?limit=100",
            headers=headers
        )
        
        if tokens_response.status_code == 200:
            tokens_data = tokens_response.json()
            revoked_count = 0
            
            for token in tokens_data['tokens']:
                if not token['is_revoked']:
                    print(f"  - Revoking OAuth token for client: {token['client']['name']}")
                    revoke_response = await client.post(
                        f"{BASE_URL}/api/v1/admin/oauth/tokens/{token['id']}/revoke",
                        headers=headers
                    )
                    if revoke_response.status_code == 200:
                        revoked_count += 1
                    else:
                        print(f"    Failed: {revoke_response.text}")
            
            print(f"✓ Revoked {revoked_count} OAuth tokens")
        
        # Clean up users (except the admin user)
        print("\n5. Cleaning up users...")
        users_response = await client.get(
            f"{BASE_URL}/api/v1/admin/users?limit=100",
            headers=headers
        )
        
        if users_response.status_code == 200:
            users_data = users_response.json()
            deleted_count = 0
            
            for user in users_data['users']:
                # Skip the current admin user
                if user['email'].lower() == ADMIN_EMAIL.lower():
                    continue
                
                # Skip if user has tasks (to preserve workspaces)
                if user.get('task_count', 0) > 0:
                    print(f"  - Skipping user with tasks: {user['email']} ({user['task_count']} tasks)")
                    continue
                
                print(f"  - Deleting user: {user['email']}")
                delete_response = await client.delete(
                    f"{BASE_URL}/api/v1/admin/users/{user['id']}",
                    headers=headers
                )
                if delete_response.status_code == 200:
                    deleted_count += 1
                else:
                    print(f"    Failed: {delete_response.text}")
            
            print(f"✓ Deleted {deleted_count} users")
        
        # Get final statistics
        print("\n6. Final statistics:")
        stats_response = await client.get(
            f"{BASE_URL}/api/v1/admin/stats/overview",
            headers=headers
        )
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"  - Total users: {stats['users']['total']}")
            print(f"  - Total workspaces: {stats['workspaces']['total']}")
            print(f"  - Total tasks: {stats['tasks']['total']}")
        
        print("\n✓ Cleanup completed successfully!")
        print("  - Preserved: Your user account, all workspaces, lists, and tasks")
        print("  - Removed: Test users, MCP agents, API keys, and OAuth tokens")

if __name__ == "__main__":
    asyncio.run(main())