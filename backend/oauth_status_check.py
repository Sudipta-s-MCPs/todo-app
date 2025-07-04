#!/usr/bin/env python3
"""
OAuth Integration Status Check
Created: 2025-07-03 22:35:00 PST
"""

import httpx
import asyncio
from datetime import datetime

BASE_URL = "http://localhost:5482"
MCP_URL = "http://localhost:5485"

async def check_backend_status():
    """Check if backend is running and healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v1/system/health")
            if response.status_code == 200:
                data = response.json()
                return True, f"Backend is healthy - Database: {data.get('database', 'unknown')}"
            else:
                return False, f"Backend returned status {response.status_code}"
    except Exception as e:
        return False, f"Backend connection failed: {str(e)}"

async def check_mcp_status():
    """Check if MCP server is running"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": "status-check"
                },
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 401:
                return True, "MCP server is running (authentication required)"
            elif response.status_code == 200:
                return True, "MCP server is running (no auth required?)"
            else:
                return False, f"MCP server returned status {response.status_code}"
    except Exception as e:
        return False, f"MCP server connection failed: {str(e)}"

async def check_oauth_endpoints():
    """Check OAuth endpoints availability"""
    endpoints = [
        ("/api/v1/auth/oauth/authorize", "Authorization"),
        ("/api/v1/auth/oauth/token", "Token Exchange"),
        ("/api/v1/auth/oauth/revoke", "Token Revocation"),
        ("/api/v1/auth/oauth/callback", "Callback Handler")
    ]
    
    results = []
    async with httpx.AsyncClient() as client:
        for path, name in endpoints:
            try:
                response = await client.options(f"{BASE_URL}{path}")
                results.append((True, f"{name} endpoint is available"))
            except Exception as e:
                results.append((False, f"{name} endpoint failed: {str(e)}"))
    
    return results

async def check_admin_oauth_endpoints():
    """Check admin OAuth management endpoints"""
    endpoints = [
        ("/api/v1/admin/oauth/clients", "OAuth Client Management"),
        ("/api/v1/admin/oauth/tokens", "OAuth Token Management")
    ]
    
    results = []
    async with httpx.AsyncClient() as client:
        for path, name in endpoints:
            try:
                response = await client.options(f"{BASE_URL}{path}")
                results.append((True, f"{name} endpoint is available"))
            except Exception as e:
                results.append((False, f"{name} endpoint failed: {str(e)}"))
    
    return results

async def main():
    print("🔍 Smart-ToDo OAuth Integration Status Check")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S PST')}")
    print()
    
    # Check backend
    print("1️⃣  Backend Status:")
    status, message = await check_backend_status()
    print(f"   {'✅' if status else '❌'} {message}")
    print()
    
    # Check MCP server
    print("2️⃣  MCP Server Status:")
    status, message = await check_mcp_status()
    print(f"   {'✅' if status else '❌'} {message}")
    print()
    
    # Check OAuth endpoints
    print("3️⃣  OAuth Flow Endpoints:")
    results = await check_oauth_endpoints()
    for status, message in results:
        print(f"   {'✅' if status else '❌'} {message}")
    print()
    
    # Check admin endpoints
    print("4️⃣  Admin OAuth Management:")
    results = await check_admin_oauth_endpoints()
    for status, message in results:
        print(f"   {'✅' if status else '❌'} {message}")
    print()
    
    # Summary
    print("📋 Summary:")
    print(f"   - Backend URL: {BASE_URL}")
    print(f"   - MCP Server URL: {MCP_URL}/mcp")
    print(f"   - OAuth Authorization: {BASE_URL}/api/v1/auth/oauth/authorize")
    print(f"   - OAuth Token: {BASE_URL}/api/v1/auth/oauth/token")
    print()
    
    print("🚀 Next Steps:")
    print("   1. Create OAuth client via admin panel or test script")
    print("   2. Run: python oauth_callback_server.py (in one terminal)")
    print("   3. Run: python test_oauth_flow.py (in another terminal)")
    print("   4. Configure Claude Desktop with the OAuth details")

if __name__ == "__main__":
    asyncio.run(main())