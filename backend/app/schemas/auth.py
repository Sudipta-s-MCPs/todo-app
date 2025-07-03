"""
Authentication schemas
Created: 2025-01-30 14:12:00 PST
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from uuid import UUID

from app.models.user import DeviceType, AccessMethod


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=255)
    timezone: Optional[str] = "UTC"
    locale: Optional[str] = "en-US"


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    device_name: Optional[str] = None
    device_type: Optional[DeviceType] = DeviceType.WEB
    device_identifier: Optional[str] = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: 'UserInfo'


class TokenRefresh(BaseModel):
    refresh_token: str


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class DeviceInfo(BaseModel):
    id: UUID
    device_name: str
    device_type: DeviceType
    device_identifier: str
    is_trusted: bool
    is_active: bool
    last_used_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    permissions: List[str] = []
    expires_days: Optional[int] = None
    rate_limit: Optional[int] = 1000


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    key: str  # Only returned on creation
    permissions: List[str]
    rate_limit: int
    expires_at: Optional[datetime]
    created_at: datetime


class APIKeyInfo(BaseModel):
    id: UUID
    name: str
    permissions: List[str]
    rate_limit: int
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
    is_active: bool


class MCPAgentRegister(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=255)
    capabilities: List[str] = []
    permissions: List[str] = []


class MCPAgentResponse(BaseModel):
    id: UUID
    agent_name: str
    agent_identifier: str
    api_key: str  # Only returned on creation
    capabilities: List[str]
    permissions: List[str]
    created_at: datetime


class MCPAgentInfo(BaseModel):
    id: UUID
    agent_name: str
    agent_identifier: str
    capabilities: List[str]
    permissions: List[str]
    last_heartbeat: Optional[datetime]
    created_at: datetime
    is_active: bool


class TwoFactorEnable(BaseModel):
    password: str


class TwoFactorConfirm(BaseModel):
    totp_code: str


class TwoFactorVerify(BaseModel):
    totp_code: str


class UserInfo(BaseModel):
    id: UUID
    email: str
    name: str
    avatar_url: Optional[str]
    timezone: str
    locale: str
    is_active: bool
    is_verified: bool
    is_admin: bool
    approval_status: str
    two_factor_enabled: bool
    auth_provider: str  # local, ldap, oauth
    created_at: datetime
    last_active_at: Optional[datetime]
    
    class Config:
        from_attributes = True