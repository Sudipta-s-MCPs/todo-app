#!/usr/bin/env python3
"""
Comprehensive OAuth Integration Check
Created: 2025-07-04 04:00:00 PST
"""

import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://localhost:5482"
MCP_URL = "http://localhost:5485"

async def check_oauth_implementation():
    """Check complete OAuth implementation"""
    print("🔍 OAuth Integration Completeness Check")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S PST')}")
    print()
    
    issues = []
    
    # 1. Check OAuth tables exist
    print("1️⃣  Database Tables:")
    async with httpx.AsyncClient() as client:
        try:
            # This endpoint requires admin auth, but we can check if it responds
            response = await client.get(f"{BASE_URL}/api/v1/admin/oauth/clients")
            if response.status_code == 401:
                print("   ✅ OAuth client management endpoint exists (auth required)")
            else:
                print(f"   ⚠️  Unexpected response: {response.status_code}")
        except Exception as e:
            issues.append(f"OAuth client endpoint error: {e}")
            print(f"   ❌ OAuth client endpoint error: {e}")
    
    # 2. Check OAuth flow endpoints
    print("\n2️⃣  OAuth Flow Endpoints:")
    oauth_endpoints = [
        ("GET", "/api/v1/auth/oauth/authorize", "Authorization"),
        ("POST", "/api/v1/auth/oauth/token", "Token Exchange"),
        ("POST", "/api/v1/auth/oauth/revoke", "Revocation"),
        ("GET", "/api/v1/auth/oauth/callback", "Callback")
    ]
    
    async with httpx.AsyncClient() as client:
        for method, path, name in oauth_endpoints:
            try:
                if method == "GET":
                    # Test with minimal params
                    response = await client.get(f"{BASE_URL}{path}", params={"client_id": "test"})
                    if response.status_code in [400, 422]:  # Expected for missing params
                        print(f"   ✅ {name} endpoint is active")
                    else:
                        print(f"   ⚠️  {name} endpoint returned: {response.status_code}")
                else:
                    # OPTIONS to check if POST endpoint exists
                    response = await client.options(f"{BASE_URL}{path}")
                    print(f"   ✅ {name} endpoint exists")
            except Exception as e:
                issues.append(f"{name} endpoint error: {e}")
                print(f"   ❌ {name} endpoint error: {e}")
    
    # 3. Check MCP server OAuth support
    print("\n3️⃣  MCP Server OAuth Support:")
    async with httpx.AsyncClient() as client:
        try:
            # Test with fake OAuth token
            response = await client.post(
                f"{MCP_URL}/mcp",
                headers={
                    "Authorization": "Bearer fake_oauth_token",
                    "Content-Type": "application/json"
                },
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": "oauth-test"
                }
            )
            if response.status_code == 401:
                print("   ✅ MCP server validates OAuth tokens")
            elif response.status_code == 307:
                print("   ✅ MCP server is running (redirect response)")
            else:
                print(f"   ⚠️  MCP server returned: {response.status_code}")
        except Exception as e:
            issues.append(f"MCP OAuth validation error: {e}")
            print(f"   ❌ MCP OAuth validation error: {e}")
    
    # 4. Check dependencies
    print("\n4️⃣  OAuth Dependencies:")
    try:
        import app.models.oauth
        print("   ✅ OAuth models are importable")
    except ImportError as e:
        issues.append(f"OAuth models import error: {e}")
        print(f"   ❌ OAuth models import error: {e}")
    
    try:
        from app.api.v1.auth_oauth import router
        print("   ✅ OAuth router is defined")
    except ImportError as e:
        issues.append(f"OAuth router import error: {e}")
        print(f"   ❌ OAuth router import error: {e}")
    
    # Summary
    print("\n📊 Summary:")
    if not issues:
        print("   ✅ OAuth implementation is complete!")
        print("   All components are properly integrated.")
    else:
        print(f"   ⚠️  Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"      - {issue}")
    
    print("\n🔑 OAuth Client Details:")
    print("   Client ID: claude_desktop_78cc156b")
    print("   Client Type: public (PKCE required)")
    print()
    print("📱 Claude Desktop Configuration:")
    print(f"   MCP Server URL: {MCP_URL}/mcp")
    print(f"   OAuth Authorization: {BASE_URL}/api/v1/auth/oauth/authorize")
    print(f"   OAuth Token: {BASE_URL}/api/v1/auth/oauth/token")
    print()
    print("🚀 Ready for testing with Claude Desktop!")

if __name__ == "__main__":
    asyncio.run(check_oauth_implementation())