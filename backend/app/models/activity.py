"""
Activity logging and tracking models
Created: 2025-01-30 14:04:00 PST
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, 
    Enum, Text, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.user import AccessMethod


class ActionType(str, enum.Enum):
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_RESET = "password_reset"
    PASSWORD_CHANGE = "password_change"
    TWO_FACTOR_ENABLE = "two_factor_enable"
    TWO_FACTOR_DISABLE = "two_factor_disable"
    
    # User actions
    PROFILE_UPDATE = "profile_update"
    SETTINGS_UPDATE = "settings_update"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    DEVICE_ADD = "device_add"
    DEVICE_REMOVE = "device_remove"
    DEVICE_TRUST = "device_trust"
    
    # API Key actions
    API_KEY_CREATE = "api_key_create"
    API_KEY_DELETE = "api_key_delete"
    API_KEY_UPDATE = "api_key_update"
    
    # MCP actions
    MCP_AGENT_REGISTER = "mcp_agent_register"
    MCP_AGENT_UPDATE = "mcp_agent_update"
    MCP_AGENT_DELETE = "mcp_agent_delete"
    
    # Workspace actions
    WORKSPACE_CREATE = "workspace_create"
    WORKSPACE_UPDATE = "workspace_update"
    WORKSPACE_DELETE = "workspace_delete"
    WORKSPACE_MEMBER_ADD = "workspace_member_add"
    WORKSPACE_MEMBER_REMOVE = "workspace_member_remove"
    WORKSPACE_MEMBER_ROLE_CHANGE = "workspace_member_role_change"
    
    # List actions
    LIST_CREATE = "list_create"
    LIST_UPDATE = "list_update"
    LIST_DELETE = "list_delete"
    LIST_ARCHIVE = "list_archive"
    LIST_UNARCHIVE = "list_unarchive"
    
    # Task actions
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    TASK_COMPLETE = "task_complete"
    TASK_REOPEN = "task_reopen"
    TASK_ASSIGN = "task_assign"
    TASK_UNASSIGN = "task_unassign"
    TASK_MOVE = "task_move"
    TASK_COMMENT = "task_comment"
    TASK_ATTACHMENT_ADD = "task_attachment_add"
    TASK_ATTACHMENT_DELETE = "task_attachment_delete"
    
    # System actions
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PERMISSION_DENIED = "permission_denied"
    ERROR = "error"


class ResourceType(str, enum.Enum):
    USER = "user"
    DEVICE = "device"
    API_KEY = "api_key"
    MCP_AGENT = "mcp_agent"
    SESSION = "session"
    WORKSPACE = "workspace"
    LIST = "list"
    TASK = "task"
    COMMENT = "comment"
    ATTACHMENT = "attachment"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # User and action
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action_type = Column(String(50), nullable=False)
    
    # Resource information
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Attribution
    device_id = Column(UUID(as_uuid=True), ForeignKey("user_devices.id"), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("user_sessions.id"), nullable=True)
    access_method = Column(String(50), nullable=False)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)
    mcp_agent_id = Column(UUID(as_uuid=True), ForeignKey("mcp_agents.id"), nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(36), nullable=True)
    
    # Additional data
    details = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="activities")
    device = relationship("UserDevice", foreign_keys=[device_id])
    session = relationship("UserSession", back_populates="activities")
    api_key = relationship("APIKey", back_populates="activities")
    mcp_agent = relationship("MCPAgent", back_populates="activities")
    
    __table_args__ = (
        Index('idx_activity_user_created', 'user_id', 'created_at'),
        Index('idx_activity_resource', 'resource_type', 'resource_id'),
        Index('idx_activity_action_created', 'action_type', 'created_at'),
    )