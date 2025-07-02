"""
Workspace and list schemas
Created: 2025-01-30 14:20:00 PST
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

from app.models.workspace import WorkspaceType, WorkspaceRole, ListType


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: WorkspaceType = WorkspaceType.PERSONAL
    settings: Optional[Dict[str, Any]] = {}


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    settings: Optional[Dict[str, Any]] = None


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    type: WorkspaceType
    owner_id: UUID
    settings_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    member_count: Optional[int] = 1
    task_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class WorkspaceMemberAdd(BaseModel):
    user_email: str
    role: WorkspaceRole = WorkspaceRole.MEMBER
    permissions: Optional[Dict[str, Any]] = {}


class WorkspaceMemberUpdate(BaseModel):
    role: Optional[WorkspaceRole] = None
    permissions: Optional[Dict[str, Any]] = None


class WorkspaceMemberResponse(BaseModel):
    workspace_id: UUID
    user_id: UUID
    user_email: str
    user_name: str
    role: WorkspaceRole
    permissions_json: Dict[str, Any]
    joined_at: datetime
    invited_by: Optional[UUID]
    
    class Config:
        from_attributes = True


class ListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    color: Optional[str] = "#000000"
    icon: Optional[str] = None
    type: ListType = ListType.DEFAULT
    position: Optional[int] = 0
    settings: Optional[Dict[str, Any]] = {}


class ListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    color: Optional[str] = None
    icon: Optional[str] = None
    position: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None


class ListResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    color: str
    icon: Optional[str]
    type: ListType
    position: int
    settings_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    is_default: bool
    task_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class ListReorder(BaseModel):
    list_ids: List[UUID]