"""
Task-related database models
Created: 2025-01-30 14:03:00 PST
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, 
    Enum as SQLEnum, Text, JSON, Integer, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.user import AccessMethod


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    list_id = Column(UUID(as_uuid=True), ForeignKey("lists.id"), nullable=False)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO, nullable=False)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    
    # Attribution fields
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_via_device_id = Column(UUID(as_uuid=True), ForeignKey("user_devices.id"), nullable=True)
    created_via_method = Column(String(50), nullable=False)
    created_via_session_id = Column(UUID(as_uuid=True), ForeignKey("user_sessions.id"), nullable=True)
    
    # Task fields
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    
    # Metadata
    position = Column(Integer, default=0)
    task_metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Duplicate detection
    similarity_hash = Column(String(64), nullable=True, index=True)
    
    # Relationships
    list = relationship("List", back_populates="tasks")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    created_device = relationship("UserDevice", foreign_keys=[created_via_device_id])
    created_session = relationship("UserSession", foreign_keys=[created_via_session_id])
    
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    assignments = relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")
    modifications = relationship("TaskModification", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")


class TaskAssignment(Base):
    __tablename__ = "task_assignments"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="assignments")
    user = relationship("User", foreign_keys=[user_id], back_populates="assigned_tasks")
    assigner = relationship("User", foreign_keys=[assigned_by])


class TaskModification(Base):
    __tablename__ = "task_modifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    
    field_name = Column(String(50), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    
    # Attribution
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_via_device_id = Column(UUID(as_uuid=True), ForeignKey("user_devices.id"), nullable=True)
    modified_via_method = Column(String(50), nullable=False)
    modified_via_session_id = Column(UUID(as_uuid=True), ForeignKey("user_sessions.id"), nullable=True)
    
    modified_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="modifications")
    modifier = relationship("User", foreign_keys=[modified_by])
    modified_device = relationship("UserDevice", foreign_keys=[modified_via_device_id])
    modified_session = relationship("UserSession", foreign_keys=[modified_via_session_id])


class TaskComment(Base):
    __tablename__ = "task_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    
    content = Column(Text, nullable=False)
    
    # Attribution
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_via_device_id = Column(UUID(as_uuid=True), ForeignKey("user_devices.id"), nullable=True)
    created_via_method = Column(String(50), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User", foreign_keys=[created_by])
    created_device = relationship("UserDevice", foreign_keys=[created_via_device_id])


class TaskAttachment(Base):
    __tablename__ = "task_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)
    
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])