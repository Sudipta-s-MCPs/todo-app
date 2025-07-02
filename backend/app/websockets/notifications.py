"""
WebSocket notification utilities
Created: 2025-01-30 15:01:00 PST
"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from .manager import manager
from .events import WebSocketEvent, EventType
from app.models.task import Task
from app.models.workspace import Workspace, List


class NotificationService:
    """Service for sending WebSocket notifications"""
    
    @staticmethod
    async def notify_task_created(
        task: Task,
        workspace_id: UUID,
        list_id: UUID,
        created_by: UUID,
        device_id: str
    ):
        """Notify about task creation"""
        event = WebSocketEvent(
            type=EventType.TASK_CREATED,
            timestamp=datetime.utcnow(),
            data={
                "task": {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "list_id": str(list_id),
                    "created_by": str(created_by),
                    "created_at": task.created_at.isoformat()
                }
            },
            workspace_id=workspace_id,
            list_id=list_id,
            task_id=task.id,
            user_id=created_by,
            device_id=device_id
        )
        
        await manager.broadcast_to_workspace(workspace_id, event, exclude_user=created_by)
    
    @staticmethod
    async def notify_task_updated(
        task: Task,
        workspace_id: UUID,
        list_id: UUID,
        updated_by: UUID,
        device_id: str,
        changes: Dict[str, Any]
    ):
        """Notify about task update"""
        event = WebSocketEvent(
            type=EventType.TASK_UPDATED,
            timestamp=datetime.utcnow(),
            data={
                "task_id": str(task.id),
                "changes": changes,
                "updated_by": str(updated_by),
                "updated_at": task.updated_at.isoformat()
            },
            workspace_id=workspace_id,
            list_id=list_id,
            task_id=task.id,
            user_id=updated_by,
            device_id=device_id
        )
        
        await manager.broadcast_to_workspace(workspace_id, event, exclude_user=updated_by)
    
    @staticmethod
    async def notify_task_deleted(
        task_id: UUID,
        workspace_id: UUID,
        list_id: UUID,
        deleted_by: UUID,
        device_id: str
    ):
        """Notify about task deletion"""
        event = WebSocketEvent(
            type=EventType.TASK_DELETED,
            timestamp=datetime.utcnow(),
            data={
                "task_id": str(task_id),
                "deleted_by": str(deleted_by)
            },
            workspace_id=workspace_id,
            list_id=list_id,
            task_id=task_id,
            user_id=deleted_by,
            device_id=device_id
        )
        
        await manager.broadcast_to_workspace(workspace_id, event, exclude_user=deleted_by)
    
    @staticmethod
    async def notify_task_moved(
        task: Task,
        workspace_id: UUID,
        from_list_id: UUID,
        to_list_id: UUID,
        moved_by: UUID,
        device_id: str
    ):
        """Notify about task being moved between lists"""
        event = WebSocketEvent(
            type=EventType.TASK_MOVED,
            timestamp=datetime.utcnow(),
            data={
                "task_id": str(task.id),
                "from_list_id": str(from_list_id),
                "to_list_id": str(to_list_id),
                "moved_by": str(moved_by)
            },
            workspace_id=workspace_id,
            task_id=task.id,
            user_id=moved_by,
            device_id=device_id
        )
        
        await manager.broadcast_to_workspace(workspace_id, event, exclude_user=moved_by)
    
    @staticmethod
    async def notify_list_created(
        list_obj: List,
        workspace_id: UUID,
        created_by: UUID,
        device_id: str
    ):
        """Notify about list creation"""
        event = WebSocketEvent(
            type=EventType.LIST_CREATED,
            timestamp=datetime.utcnow(),
            data={
                "list": {
                    "id": str(list_obj.id),
                    "name": list_obj.name,
                    "color": list_obj.color,
                    "position": list_obj.position,
                    "created_by": str(created_by)
                }
            },
            workspace_id=workspace_id,
            list_id=list_obj.id,
            user_id=created_by,
            device_id=device_id
        )
        
        await manager.broadcast_to_workspace(workspace_id, event, exclude_user=created_by)
    
    @staticmethod
    async def notify_list_updated(
        list_obj: List,
        workspace_id: UUID,
        updated_by: UUID,
        device_id: str,
        changes: Dict[str, Any]
    ):
        """Notify about list update"""
        event = WebSocketEvent(
            type=EventType.LIST_UPDATED,
            timestamp=datetime.utcnow(),
            data={
                "list_id": str(list_obj.id),
                "changes": changes,
                "updated_by": str(updated_by)
            },
            workspace_id=workspace_id,
            list_id=list_obj.id,
            user_id=updated_by,
            device_id=device_id
        )
        
        await manager.broadcast_to_workspace(workspace_id, event, exclude_user=updated_by)
    
    @staticmethod
    async def notify_workspace_updated(
        workspace: Workspace,
        updated_by: UUID,
        device_id: str,
        changes: Dict[str, Any]
    ):
        """Notify about workspace update"""
        event = WebSocketEvent(
            type=EventType.WORKSPACE_UPDATED,
            timestamp=datetime.utcnow(),
            data={
                "workspace_id": str(workspace.id),
                "changes": changes,
                "updated_by": str(updated_by)
            },
            workspace_id=workspace.id,
            user_id=updated_by,
            device_id=device_id
        )
        
        await manager.broadcast_to_workspace(workspace.id, event, exclude_user=updated_by)


# Global notification service instance
notifications = NotificationService()