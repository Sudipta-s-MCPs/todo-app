"""
WebSocket event types and models
Created: 2025-01-30 15:01:00 PST
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class EventType(str, Enum):
    """WebSocket event types"""
    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_MOVED = "task.moved"
    TASK_ASSIGNED = "task.assigned"
    TASK_UNASSIGNED = "task.unassigned"
    TASK_COMMENTED = "task.commented"
    
    # List events
    LIST_CREATED = "list.created"
    LIST_UPDATED = "list.updated"
    LIST_DELETED = "list.deleted"
    LIST_REORDERED = "list.reordered"
    
    # Workspace events
    WORKSPACE_UPDATED = "workspace.updated"
    WORKSPACE_MEMBER_ADDED = "workspace.member_added"
    WORKSPACE_MEMBER_REMOVED = "workspace.member_removed"
    
    # User events
    USER_PRESENCE_CHANGED = "user.presence_changed"
    USER_TYPING = "user.typing"
    USER_STOPPED_TYPING = "user.stopped_typing"
    
    # Collaboration events
    COLLABORATION_STARTED = "collaboration.started"
    COLLABORATION_ENDED = "collaboration.ended"
    COLLABORATION_CURSOR_MOVED = "collaboration.cursor_moved"


class WebSocketEvent(BaseModel):
    """WebSocket event model"""
    type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    workspace_id: Optional[UUID] = None
    list_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    device_id: Optional[str] = None
    correlation_id: Optional[str] = None


class UserPresence(BaseModel):
    """User presence information"""
    user_id: UUID
    status: str  # online, away, offline
    last_seen: datetime
    active_workspace_id: Optional[UUID] = None
    active_list_id: Optional[UUID] = None
    active_task_id: Optional[UUID] = None


class TypingIndicator(BaseModel):
    """Typing indicator event"""
    user_id: UUID
    workspace_id: UUID
    list_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    is_typing: bool


class CursorPosition(BaseModel):
    """Cursor position for collaborative editing"""
    user_id: UUID
    task_id: UUID
    field: str  # title, description, etc.
    position: int
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None