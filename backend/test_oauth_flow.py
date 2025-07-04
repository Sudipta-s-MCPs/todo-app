#!/usr/bin/env python3
"""
OAuth Flow Test Script for Claude Desktop Integration
Created: 2025-07-03 22:15:00 PST
"""

import asyncio
import httpx
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs
import secrets
import hashlib
import base64

# Configuration
BASE_URL = "http://localhost:5482"
API_BASE = f"{BASE_URL}/api/v1"
MCP_SERVER_URL = "http://localhost:5485/mcp"

# Test OAuth client details
CLIENT_ID = None  # Will be set after client creation
CLIENT_SECRET = None  # Only for confidential clients


def generate_code_verifier():
    """Generate PKCE code verifier"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')


def generate_code_challenge(verifier):
    """Generate PKCE code challenge from verifier"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')


async def create_oauth_client():
    """Create an OAuth client for testing"""
    print("\n1. Creating OAuth client...")
    
    # First, get admin token (you'll need to provide your admin credentials)
    admin_email = input("Enter admin email: ")
    admin_password = input("Enter admin password: ")
    
    async with httpx.AsyncClient() as client:
        # Login as admin
        login_response = await client.post(
            f"{API_BASE}/auth/login",
            data={
                "username": admin_email,
                "password": admin_password
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Admin login failed: {login_response.text}")
            return None, None
        
        admin_token = login_response.json()["access_token"]
        
        # Create OAuth client
        create_response = await client.post(
            f"{API_BASE}/admin/oauth/clients",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "client_name": "Claude Desktop Test",
                "client_type": "public",
                "redirect_uris": [
                    "http://localhost:5482/api/v1/auth/oauth/callback",
                    "http://localhost:5484/oauth/callback",
                    "http://localhost:*",
                    "claude://oauth/callback"
                ],
                "allowed_scopes": ["read", "write"]
            }
        )
        
        if create_response.status_code != 201:
            print(f"❌ OAuth client creation failed: {create_response.text}")
            return None, None
        
        client_data = create_response.json()
        print(f"✅ OAuth client created successfully!")
        print(f"   Client ID: {client_data['client_id']}")
        print(f"   Client Name: {client_data['client_name']}")
        
        return client_data['client_id'], None  # No secret for public clients


async def test_authorization_flow(client_id):
    """Test the OAuth authorization flow"""
    print("\n2. Testing OAuth authorization flow...")
    
    # Generate PKCE parameters
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(16)
    
    # Build authorization URL
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": "http://localhost:5482/api/v1/auth/oauth/callback",
        "scope": "read write",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    
    auth_url = f"{API_BASE}/auth/oauth/authorize?{urlencode(auth_params)}"
    
    print(f"\n📌 Authorization URL:")
    print(f"   {auth_url}")
    print(f"\n📋 PKCE Details:")
    print(f"   Code Verifier: {code_verifier}")
    print(f"   Code Challenge: {code_challenge}")
    print(f"   State: {state}")
    
    # Open in browser
    print("\n🌐 Opening authorization URL in browser...")
    print("   Please login and authorize the application.")
    print("   After authorization, you'll be redirected to the callback page.")
    webbrowser.open(auth_url)
    
    # Wait for user to complete authorization
    print("\n   Copy the authorization code from the callback page.")
    auth_code = input("✏️  Enter the authorization code: ")
    
    return auth_code, code_verifier, state


async def test_token_exchange(client_id, auth_code, code_verifier):
    """Test exchanging authorization code for tokens"""
    print("\n3. Testing token exchange...")
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{API_BASE}/auth/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": "http://localhost:5482/api/v1/auth/oauth/callback",
                "client_id": client_id,
                "code_verifier": code_verifier
            }
        )
        
        if token_response.status_code != 200:
            print(f"❌ Token exchange failed: {token_response.text}")
            return None
        
        tokens = token_response.json()
        print(f"✅ Token exchange successful!")
        print(f"   Access Token: {tokens['access_token'][:20]}...")
        print(f"   Token Type: {tokens['token_type']}")
        print(f"   Expires In: {tokens['expires_in']} seconds")
        if tokens.get('refresh_token'):
            print(f"   Refresh Token: {tokens['refresh_token'][:20]}...")
        
        return tokens


async def test_api_access(access_token):
    """Test API access with OAuth token"""
    print("\n4. Testing API access with OAuth token...")
    
    async with httpx.AsyncClient() as client:
        # Test /auth/me endpoint
        me_response = await client.get(
            f"{API_BASE}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if me_response.status_code != 200:
            print(f"❌ API access failed: {me_response.text}")
            return False
        
        user_info = me_response.json()
        print(f"✅ API access successful!")
        print(f"   User: {user_info['email']}")
        print(f"   Name: {user_info['name']}")
        
        # Test tasks endpoint
        tasks_response = await client.post(
            f"{API_BASE}/tasks/search",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"limit": 5}
        )
        
        if tasks_response.status_code == 200:
            tasks = tasks_response.json()
            print(f"   Tasks Count: {len(tasks)}")
        
        return True


async def test_mcp_access(access_token):
    """Test MCP server access with OAuth token"""
    print("\n5. Testing MCP server access with OAuth token...")
    
    async with httpx.AsyncClient() as client:
        # Test MCP server with OAuth token
        mcp_response = await client.post(
            MCP_SERVER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": "test-1"
            }
        )
        
        if mcp_response.status_code != 200:
            print(f"❌ MCP server access failed: {mcp_response.text}")
            return False
        
        mcp_data = mcp_response.json()
        print(f"✅ MCP server access successful!")
        if "result" in mcp_data and "tools" in mcp_data["result"]:
            print(f"   Available tools: {len(mcp_data['result']['tools'])}")
            for tool in mcp_data['result']['tools'][:3]:
                print(f"   - {tool['name']}")
        
        return True


async def test_token_refresh(client_id, refresh_token):
    """Test refreshing access token"""
    print("\n6. Testing token refresh...")
    
    if not refresh_token:
        print("⚠️  No refresh token available (normal for some flows)")
        return None
    
    async with httpx.AsyncClient() as client:
        refresh_response = await client.post(
            f"{API_BASE}/auth/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id
            }
        )
        
        if refresh_response.status_code != 200:
            print(f"❌ Token refresh failed: {refresh_response.text}")
            return None
        
        new_tokens = refresh_response.json()
        print(f"✅ Token refresh successful!")
        print(f"   New Access Token: {new_tokens['access_token'][:20]}...")
        
        return new_tokens


async def test_token_revocation(client_id, access_token):
    """Test revoking tokens"""
    print("\n7. Testing token revocation...")
    
    async with httpx.AsyncClient() as client:
        revoke_response = await client.post(
            f"{API_BASE}/auth/oauth/revoke",
            data={
                "token": access_token,
                "client_id": client_id
            }
        )
        
        if revoke_response.status_code != 200:
            print(f"❌ Token revocation failed: {revoke_response.text}")
            return False
        
        print(f"✅ Token revocation successful!")
        
        # Verify token is revoked
        verify_response = await client.get(
            f"{API_BASE}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if verify_response.status_code == 401:
            print(f"   ✅ Token is no longer valid")
            return True
        else:
            print(f"   ❌ Token is still valid (unexpected)")
            return False


async def main():
    """Run all OAuth flow tests"""
    print("🚀 Smart-ToDo OAuth Flow Test Suite")
    print("===================================")
    
    # Create OAuth client
    client_id, client_secret = await create_oauth_client()
    if not client_id:
        return
    
    # Test authorization flow
    auth_code, code_verifier, state = await test_authorization_flow(client_id)
    if not auth_code:
        return
    
    # Test token exchange
    tokens = await test_token_exchange(client_id, auth_code, code_verifier)
    if not tokens:
        return
    
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")
    
    # Test API access
    await test_api_access(access_token)
    
    # Test MCP server access
    await test_mcp_access(access_token)
    
    # Test token refresh
    if refresh_token:
        new_tokens = await test_token_refresh(client_id, refresh_token)
        if new_tokens:
            # Use new access token for subsequent tests
            access_token = new_tokens["access_token"]
    
    # Test token revocation
    await test_token_revocation(client_id, access_token)
    
    print("\n✅ OAuth flow test complete!")
    print("\n📝 Claude Desktop Configuration:")
    print(f"   Server URL: {MCP_SERVER_URL}")
    print(f"   OAuth Authorization URL: {API_BASE}/auth/oauth/authorize")
    print(f"   OAuth Token URL: {API_BASE}/auth/oauth/token")
    print(f"   Client ID: {client_id}")


if __name__ == "__main__":
    asyncio.run(main())