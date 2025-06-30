"""
Task schemas
Created: 2025-01-30 14:25:00 PST
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID

from app.models.task import TaskStatus, TaskPriority
from app.models.user import AccessMethod


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    parent_task_id: Optional[UUID] = None
    assigned_to: Optional[List[UUID]] = []
    metadata: Optional[Dict[str, Any]] = {}


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    list_id: Optional[UUID] = None
    position: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    id: UUID
    list_id: UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    
    created_by: UUID
    created_via_device_id: Optional[UUID]
    created_via_method: AccessMethod
    created_via_session_id: Optional[UUID]
    
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    parent_task_id: Optional[UUID]
    
    position: int
    metadata: Dict[str, Any]
    
    created_at: datetime
    updated_at: datetime
    
    # Additional fields populated by API
    creator_name: Optional[str] = None
    assigned_users: Optional[List[Dict[str, Any]]] = []
    subtask_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    attachment_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class TaskAssignmentCreate(BaseModel):
    user_ids: List[UUID]


class TaskCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)


class TaskCommentResponse(BaseModel):
    id: UUID
    task_id: UUID
    content: str
    created_by: UUID
    created_via_device_id: Optional[UUID]
    created_via_method: AccessMethod
    created_at: datetime
    updated_at: datetime
    
    # Additional fields
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None
    
    class Config:
        from_attributes = True


class TaskAttachmentResponse(BaseModel):
    id: UUID
    task_id: UUID
    filename: str
    file_size: int
    mime_type: str
    uploaded_by: UUID
    uploaded_at: datetime
    
    # Additional fields
    uploader_name: Optional[str] = None
    download_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class TaskMoveRequest(BaseModel):
    list_id: UUID
    position: Optional[int] = None


class TaskBulkOperation(BaseModel):
    task_ids: List[UUID]
    operation: str  # "delete", "complete", "archive", "move"
    list_id: Optional[UUID] = None  # For move operation


class DuplicateCheckResult(BaseModel):
    has_duplicates: bool
    duplicates: List[TaskResponse] = []
    similarity_scores: Optional[Dict[str, float]] = {}


class TaskSearchQuery(BaseModel):
    query: Optional[str] = None
    workspace_id: Optional[UUID] = None
    list_ids: Optional[List[UUID]] = []
    status: Optional[List[TaskStatus]] = []
    priority: Optional[List[TaskPriority]] = []
    assigned_to: Optional[List[UUID]] = []
    created_by: Optional[UUID] = None
    due_before: Optional[datetime] = None
    due_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    created_after: Optional[datetime] = None
    has_attachments: Optional[bool] = None
    parent_task_id: Optional[UUID] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)