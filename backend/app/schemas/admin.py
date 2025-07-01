"""
Admin schemas for user, MCP agent, and API key management
Created: 2025-01-30 23:50:00 PST
"""

from datetime import datetime
from typing import Optional, List, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int


class UserAdminInfo(BaseModel):
    """User information for admin panel"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    name: str
    is_active: bool
    is_admin: bool
    is_verified: bool
    two_factor_enabled: bool
    auth_provider: str
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    workspace_count: int = 0
    task_count: int = 0


class UserAdminCreate(BaseModel):
    """Create user as admin"""
    email: str
    name: str
    password: str
    is_admin: bool = False


class UserAdminUpdate(BaseModel):
    """Update user information as admin"""
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_verified: Optional[bool] = None


class APIKeyAdminInfo(BaseModel):
    """API key information for admin panel"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    key_prefix: str
    user_id: str
    user_email: str
    permissions: List[str]
    rate_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime
    is_active: bool
    request_count: int = 0


class MCPAgentAdminInfo(BaseModel):
    """MCP agent information for admin panel"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    agent_id: str  # agent_identifier
    name: str  # agent_name
    description: str
    user_id: str
    user_email: str
    is_active: bool
    last_heartbeat: Optional[datetime] = None
    created_at: datetime
    request_count: int = 0
    permissions: List[str]
    capabilities: List[str]