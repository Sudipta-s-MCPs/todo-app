#!/usr/bin/env python3
"""
Create OAuth client for Claude Desktop
Created: 2025-07-04 03:15:00 PST
"""

import asyncio
import sys
import os
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.oauth import OAuthClient
from app.utils.security import get_password_hash


async def create_claude_desktop_oauth_client():
    """Create OAuth client for Claude Desktop"""
    async with AsyncSessionLocal() as db:
        try:
            # Check if client already exists
            result = await db.execute(
                select(OAuthClient).where(
                    OAuthClient.client_name == "Claude Desktop"
                )
            )
            existing_client = result.scalar_one_or_none()
            
            if existing_client:
                print(f"OAuth client 'Claude Desktop' already exists with client_id: {existing_client.client_id}")
                return
            
            # Generate client credentials
            client_id = f"claude_desktop_{uuid4().hex[:8]}"
            client_secret = f"cs_{uuid4().hex}"
            
            # Create OAuth client
            oauth_client = OAuthClient(
                client_id=client_id,
                client_secret_hash=get_password_hash(client_secret),
                client_name="Claude Desktop",
                client_type="public",  # Public client (no client secret required)
                redirect_uris=[
                    "http://localhost:5482/api/v1/auth/oauth/callback",
                    "http://localhost:5484/oauth/callback",
                    "http://localhost:*",
                    "claude://oauth/callback",
                    "http://127.0.0.1:5482/api/v1/auth/oauth/callback",
                    "http://127.0.0.1:5484/oauth/callback"
                ],
                allowed_scopes=["read", "write", "tasks", "lists", "workspaces"]
            )
            
            db.add(oauth_client)
            await db.commit()
            
            print(f"""
OAuth Client Created Successfully!
================================

Client Name: Claude Desktop
Client ID: {client_id}
Client Secret: {client_secret}
Client Type: public (PKCE supported)

Redirect URIs:
- http://localhost:5482/api/v1/auth/oauth/callback (Backend OAuth callback)
- http://localhost:5484/oauth/callback (Frontend OAuth callback)
- http://localhost:* (wildcard for Claude Desktop dynamic ports)
- claude://oauth/callback (Claude Desktop custom scheme)
- http://127.0.0.1:5482/api/v1/auth/oauth/callback
- http://127.0.0.1:5484/oauth/callback

OAuth Endpoints:
- Authorization: http://localhost:5482/api/v1/auth/oauth/authorize
- Token: http://localhost:5482/api/v1/auth/oauth/token
- Revoke: http://localhost:5482/api/v1/auth/oauth/revoke

Example Authorization URL:
http://localhost:5482/api/v1/auth/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri=http://localhost:5482/api/v1/auth/oauth/callback&scope=read%20write&state=random_state

Note: Save the client_id and client_secret securely!
""")
            
        except Exception as e:
            print(f"Error creating OAuth client: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(create_claude_desktop_oauth_client())