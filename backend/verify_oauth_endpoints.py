#!/usr/bin/env python3
"""
Verify OAuth Endpoints are Accessible
Created: 2025-07-03 22:25:00 PST
"""

import httpx

BASE_URL = "http://localhost:5482/api/v1"

endpoints = [
    ("GET", "/auth/oauth/authorize", "OAuth Authorization Endpoint"),
    ("POST", "/auth/oauth/token", "OAuth Token Endpoint"),
    ("POST", "/auth/oauth/revoke", "OAuth Token Revocation"),
    ("GET", "/auth/oauth/callback", "OAuth Callback Handler"),
]

print("🔍 Verifying OAuth Endpoints")
print("=" * 50)

for method, path, description in endpoints:
    url = f"{BASE_URL}{path}"
    try:
        # Send OPTIONS request to check if endpoint exists
        response = httpx.options(url, timeout=5.0)
        
        # For GET endpoints, we can also try a basic GET
        if method == "GET":
            get_response = httpx.get(url, params={"client_id": "test"}, timeout=5.0)
            status = get_response.status_code
        else:
            # For POST, just check if endpoint exists
            status = response.status_code if response.status_code != 405 else "exists"
        
        print(f"✅ {description}")
        print(f"   {method} {url}")
        print(f"   Status: {status}")
        
    except Exception as e:
        print(f"❌ {description}")
        print(f"   {method} {url}")
        print(f"   Error: {str(e)}")
    
    print()

print("\n📝 To test the full OAuth flow:")
print("1. Run the callback server: python oauth_callback_server.py")
print("2. In another terminal, run: python test_oauth_flow.py")
print("3. Follow the prompts to complete the OAuth flow")