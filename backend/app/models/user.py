"""
User-related database models
Created: 2025-01-30 14:00:00 PST
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, 
    Enum as SQLEnum, Text, JSON, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class DeviceType(str, enum.Enum):
    WEB = "web"
    MOBILE_IOS = "mobile_ios"
    MOBILE_ANDROID = "mobile_android"
    DESKTOP = "desktop"
    API = "api"
    MCP_AGENT = "mcp_agent"
    OTHER = "other"


class AccessMethod(str, enum.Enum):
    WEB = "web"
    MOBILE_APP = "mobile_app"
    DESKTOP_APP = "desktop_app"
    API_KEY = "api_key"
    MCP = "mcp"
    OAUTH = "oauth"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for LDAP users
    avatar_url = Column(String(500), nullable=True)
    settings_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = Column(DateTime, nullable=True)
    
    timezone = Column(String(50), default="UTC")
    locale = Column(String(10), default="en-US")
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    # Two-factor authentication
    totp_secret = Column(String(32), nullable=True)
    two_factor_enabled = Column(Boolean, default=False)
    
    # Authentication provider
    auth_provider = Column(String(50), default="local")  # local, ldap, oauth
    ldap_dn = Column(String(500), nullable=True)  # LDAP Distinguished Name
    external_id = Column(String(500), nullable=True)  # External system ID
    
    # Relationships
    devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    mcp_agents = relationship("MCPAgent", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    owned_workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    workspace_memberships = relationship("WorkspaceMember", foreign_keys="WorkspaceMember.user_id", back_populates="user", cascade="all, delete-orphan")
    created_tasks = relationship("Task", foreign_keys="Task.created_by", back_populates="creator")
    assigned_tasks = relationship("TaskAssignment", foreign_keys="TaskAssignment.user_id", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")


class UserDevice(Base):
    __tablename__ = "user_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_name = Column(String(255), nullable=False)
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    device_identifier = Column(String(255), nullable=False)  # Unique per user
    platform_details = Column(JSON, default=dict)
    
    last_ip_address = Column(String(45), nullable=True)
    last_location = Column(String(255), nullable=True)
    
    is_trusted = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="devices")
    sessions = relationship("UserSession", back_populates="device", cascade="all, delete-orphan")
    
    # Partitioning disabled due to PostgreSQL constraint requirements
    # __table_args__ = (
    #     {"postgresql_partition_by": "LIST (user_id)"},
    # )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    permissions = Column(JSON, default=list)
    
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    expires_at = Column(DateTime, nullable=True)
    
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    activities = relationship("ActivityLog", back_populates="api_key", cascade="all, delete-orphan")


class MCPAgent(Base):
    __tablename__ = "mcp_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_name = Column(String(255), nullable=False)
    agent_identifier = Column(String(255), unique=True, nullable=False)
    
    capabilities = Column(JSON, default=list)
    permissions = Column(JSON, default=list)
    
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="mcp_agents")
    activities = relationship("ActivityLog", back_populates="mcp_agent", cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("user_devices.id"), nullable=True)
    
    session_token = Column(String(255), unique=True, nullable=False)
    refresh_token = Column(String(255), unique=True, nullable=True)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    access_method = Column(String(50), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    device = relationship("UserDevice", back_populates="sessions")
    activities = relationship("ActivityLog", back_populates="session", cascade="all, delete-orphan")