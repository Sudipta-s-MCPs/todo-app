#!/usr/bin/env python3
"""
Test script to validate FastMCP authentication configuration
"""

import asyncio
import httpx
import json
import os

# Test configuration
BASE_URL = "http://localhost:5485"
API_KEY = os.environ.get("TODO_API_KEY", "test-api-key")


async def test_authentication():
    """Test various authentication scenarios"""
    
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        print("Testing FastMCP Authentication Configuration")
        print("=" * 50)
        
        # Test 1: No authentication
        print("\n1. Testing request without authentication...")
        try:
            response = await client.post(
                "/mcp/rpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✓ Correctly rejected unauthenticated request")
            else:
                print("   ✗ Expected 401, got:", response.text)
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 2: API Key authentication
        print("\n2. Testing API key authentication...")
        try:
            response = await client.post(
                "/mcp/rpc",
                headers={"X-API-Key": API_KEY},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 2
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✓ API key authentication successful")
                result = response.json()
                print(f"   Tools available: {len(result.get('result', {}).get('tools', []))}")
            else:
                print("   ✗ Authentication failed:", response.text)
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 3: Bearer token authentication
        print("\n3. Testing Bearer token authentication...")
        try:
            # This would normally be an OAuth token
            response = await client.post(
                "/mcp/rpc",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 3
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code in [200, 401]:
                print(f"   Response received (Bearer token validation)")
            else:
                print("   ✗ Unexpected response:", response.text)
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 4: Health endpoint (should not require auth)
        print("\n4. Testing health endpoint (no auth required)...")
        try:
            response = await client.get("/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✓ Health endpoint accessible without auth")
            else:
                print("   ✗ Health endpoint not accessible")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 5: Root MCP endpoint
        print("\n5. Testing root MCP endpoint...")
        try:
            response = await client.get("/mcp/")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✓ MCP endpoint accessible")
            else:
                print("   ✗ MCP endpoint not accessible")
        except Exception as e:
            print(f"   Error: {e}")


if __name__ == "__main__":
    print("FastMCP Authentication Test")
    print(f"Testing server at: {BASE_URL}")
    print(f"Using API key: {API_KEY[:10]}..." if API_KEY else "No API key set")
    asyncio.run(test_authentication())