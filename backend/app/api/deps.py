"""
API Dependencies
Created: 2025-01-30 14:10:00 PST
"""

from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError
import logging

from app.database import get_db
from app.models.user import User, UserDevice, APIKey, MCPAgent, UserSession, AccessMethod
from app.utils.security import decode_token, verify_api_key

logger = logging.getLogger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# API Key scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated (optional)"""
    user = None
    
    # Try JWT token first
    if token:
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                return None
                
            user_id = payload.get("sub")
            if user_id:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
        except (JWTError, ValueError):
            pass
    
    # Try API key if no JWT
    if not user and api_key:
        api_key_obj = await verify_api_key(db, api_key)
        if api_key_obj:
            result = await db.execute(
                select(User).where(User.id == api_key_obj.user_id)
            )
            user = result.scalar_one_or_none()
    
    return user


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """Get current user (required)"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current admin user"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_access_info(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> Tuple[AccessMethod, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Get access method and related IDs
    Returns: (access_method, device_id, session_id, api_key_id, mcp_agent_id)
    """
    access_method = AccessMethod.OTHER
    device_id = None
    session_id = None
    api_key_id = None
    mcp_agent_id = None
    
    # Determine access method from headers and auth
    user_agent = request.headers.get("User-Agent", "")
    
    if api_key:
        access_method = AccessMethod.API_KEY
        api_key_obj = await verify_api_key(db, api_key)
        if api_key_obj:
            api_key_id = str(api_key_obj.id)
            
            # Check if it's an MCP agent
            if "mcp" in api_key_obj.name.lower():
                access_method = AccessMethod.MCP
                # Try to find associated MCP agent
                result = await db.execute(
                    select(MCPAgent).where(
                        MCPAgent.user_id == api_key_obj.user_id,
                        MCPAgent.is_active == True
                    )
                )
                mcp_agent = result.scalar_one_or_none()
                if mcp_agent:
                    mcp_agent_id = str(mcp_agent.id)
    
    elif token:
        try:
            payload = decode_token(token)
            token_type = payload.get("type")
            
            if token_type == "access":
                # Check session info in token
                session_id = payload.get("session_id")
                device_id = payload.get("device_id")
                
                # Determine access method from user agent
                if "Mobile" in user_agent:
                    access_method = AccessMethod.MOBILE_APP
                elif "Desktop" in user_agent:
                    access_method = AccessMethod.DESKTOP_APP
                else:
                    access_method = AccessMethod.WEB
                    
            elif token_type == "mcp":
                access_method = AccessMethod.MCP
                mcp_agent_id = payload.get("agent_id")
                
        except (JWTError, ValueError):
            pass
    
    return access_method, device_id, session_id, api_key_id, mcp_agent_id


async def get_device_info(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Optional[UserDevice]:
    """Get device information from request"""
    device_id = request.headers.get("X-Device-ID")
    
    if device_id:
        result = await db.execute(
            select(UserDevice).where(
                UserDevice.id == device_id,
                UserDevice.user_id == current_user.id,
                UserDevice.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    return None