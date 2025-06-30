"""
Workspace-related database models
Created: 2025-01-30 14:02:00 PST
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, 
    Enum as SQLEnum, JSON, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class WorkspaceType(str, enum.Enum):
    PERSONAL = "personal"
    TEAM = "team"
    ORGANIZATION = "org"


class WorkspaceRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ListType(str, enum.Enum):
    DEFAULT = "default"
    SMART = "smart"
    ARCHIVED = "archived"


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(WorkspaceType), default=WorkspaceType.PERSONAL, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    settings_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    owner = relationship("User", back_populates="owned_workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    lists = relationship("List", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    
    role = Column(SQLEnum(WorkspaceRole), default=WorkspaceRole.MEMBER, nullable=False)
    permissions_json = Column(JSON, default=dict)
    
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")


class List(Base):
    __tablename__ = "lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    color = Column(String(7), default="#000000")
    icon = Column(String(50), nullable=True)
    
    type = Column(SQLEnum(ListType), default=ListType.DEFAULT, nullable=False)
    position = Column(Integer, default=0)
    settings_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    is_archived = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="lists")
    tasks = relationship("Task", back_populates="list", cascade="all, delete-orphan")