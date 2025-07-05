"""
MCP Server authentication handler
Created: 2025-01-30 14:37:00 PST
Updated: 2025-07-03 22:00:00 PST - Added OAuth support
"""

import os
import httpx
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MCPAuthManager:
    """Manages authentication for MCP server"""
    
    def __init__(self):
        self.api_key = os.environ.get("TODO_API_KEY", "")
        self.api_endpoint = os.environ.get("TODO_API_ENDPOINT", "http://localhost:8000/api/v1")
        self.device_name = os.environ.get("TODO_DEVICE_NAME", "MCP Agent")
        self.device_id = os.environ.get("TODO_DEVICE_ID", "")
        self._session_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._oauth_token: Optional[str] = None
        self._token_cache: Dict[str, Dict[str, Any]] = {}  # Cache for validated tokens
        
        # Log initialization
        logger.info("MCPAuthManager initialized")
        logger.info(f"API Key configured: {'Yes' if self.api_key else 'No'}")
        if self.api_key:
            logger.info(f"API Key ending: ...{self.api_key[-4:]}")
        logger.info(f"Device ID: {self.device_id}")
        logger.info(f"API Endpoint: {self.api_endpoint}")
    
    async def get_auth_headers(self, request_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get authentication headers based on available credentials
        Supports both API key and OAuth token authentication
        
        Args:
            request_headers: Optional headers from incoming request (for OAuth)
            
        Returns:
            Headers to use for API requests
        """
        # If request headers are provided with auth info, use them directly
        if request_headers:
            # Check for API key auth from client
            if "X-API-Key" in request_headers and request_headers["X-API-Key"]:
                logger.info("Using API key from request headers")
                return {
                    "X-API-Key": request_headers["X-API-Key"],
                    "X-User-ID": request_headers.get("X-User-ID", ""),
                    "X-Device-ID": request_headers.get("X-Device-ID", ""),
                    "X-Device-Name": request_headers.get("X-Device-Name", "MCP Agent"),
                    "X-Device-Type": "mcp_agent"
                }
            
            # Check for OAuth token in request headers
            if "Authorization" in request_headers:
                auth_header = request_headers["Authorization"]
                if auth_header.startswith("Bearer "):
                    oauth_token = auth_header[7:]
                    # Validate and use OAuth token
                    if await self.validate_oauth_token(oauth_token):
                        return {"Authorization": f"Bearer {oauth_token}"}
        
        # Fall back to environment variables (for backward compatibility)
        if self.api_key:
            logger.info("Using API key from environment variables")
            return {
                "X-API-Key": self.api_key,
                "X-Device-ID": self.device_id,
                "X-Device-Name": self.device_name,
                "X-Device-Type": "mcp_agent"
            }
        
        # No authentication available
        raise ValueError("No valid authentication credentials available")
    
    async def ensure_authenticated(self) -> Dict[str, str]:
        """
        Ensure we have a valid authentication token
        Returns headers to use for API requests
        """
        # For backward compatibility, use get_auth_headers
        return await self.get_auth_headers()
    
    async def validate_oauth_token(self, token: str) -> bool:
        """
        Validate OAuth token with the backend
        
        Args:
            token: OAuth access token
            
        Returns:
            True if token is valid, False otherwise
        """
        # Check cache first
        if token in self._token_cache:
            cached = self._token_cache[token]
            if cached["expires_at"] > datetime.utcnow():
                return True
            else:
                # Remove expired token from cache
                del self._token_cache[token]
        
        try:
            async with httpx.AsyncClient(base_url=self.api_endpoint) as client:
                # Validate token by calling the /auth/me endpoint
                response = await client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    # Cache the validation result for 5 minutes
                    self._token_cache[token] = {
                        "valid": True,
                        "expires_at": datetime.utcnow() + timedelta(minutes=5),
                        "user_info": response.json()
                    }
                    return True
                else:
                    logger.warning(f"OAuth token validation failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error validating OAuth token: {str(e)}")
            return False
    
    async def register_mcp_agent(self, user_email: str, user_password: str) -> Dict[str, Any]:
        """
        Register this MCP agent with the API and get an API key
        This is a one-time setup process
        """
        async with httpx.AsyncClient(base_url=self.api_endpoint) as client:
            # First, login as the user
            login_response = await client.post(
                "/auth/login",
                data={
                    "username": user_email,
                    "password": user_password
                },
                headers={
                    "X-Device-Name": self.device_name,
                    "X-Device-Type": "mcp_agent"
                }
            )
            login_response.raise_for_status()
            
            tokens = login_response.json()
            access_token = tokens["access_token"]
            
            # Register MCP agent
            register_response = await client.post(
                "/auth/mcp/register",
                json={
                    "agent_name": self.device_name,
                    "capabilities": [
                        "task_management",
                        "list_management",
                        "search",
                        "duplicate_detection"
                    ],
                    "permissions": [
                        "tasks:read",
                        "tasks:write",
                        "lists:read",
                        "lists:write",
                        "workspaces:read"
                    ]
                },
                headers={"Authorization": f"Bearer {access_token}"}
            )
            register_response.raise_for_status()
            
            agent_info = register_response.json()
            
            # Return the configuration to save
            return {
                "api_key": agent_info["api_key"],
                "agent_id": agent_info["id"],
                "agent_identifier": agent_info["agent_identifier"],
                "user_id": tokens.get("user_id"),
                "instructions": (
                    "Save these environment variables:\\n"
                    f"TODO_API_KEY={agent_info['api_key']}\\n"
                    f"TODO_DEVICE_ID={agent_info['agent_identifier']}\\n"
                    f"TODO_DEVICE_NAME={self.device_name}\\n"
                    f"TODO_API_ENDPOINT={self.api_endpoint}"
                )
            }


# Global instance
auth_manager = MCPAuthManager()