"""
Activity logging service
Created: 2025-01-30 14:16:00 PST
"""

from typing import Optional, Dict, Any, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models.activity import ActivityLog, ActionType, ResourceType
from app.models.user import AccessMethod

logger = logging.getLogger(__name__)


async def log_activity(
    db: AsyncSession,
    user_id: UUID,
    action_type: Union[ActionType, str],
    resource_type: Optional[Union[ResourceType, str]] = None,
    resource_id: Optional[UUID] = None,
    device_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None,
    access_method: Union[AccessMethod, str] = AccessMethod.OTHER,
    api_key_id: Optional[UUID] = None,
    mcp_agent_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> ActivityLog:
    """
    Log user activity
    """
    try:
        # Convert string values to lowercase if they're enums
        if isinstance(action_type, str):
            action_type = action_type.lower()
        elif isinstance(action_type, ActionType):
            action_type = action_type.value
            
        if isinstance(resource_type, str):
            resource_type = resource_type.lower()
        elif isinstance(resource_type, ResourceType):
            resource_type = resource_type.value
            
        if isinstance(access_method, str):
            access_method = access_method.lower()
        elif isinstance(access_method, AccessMethod):
            access_method = access_method.value
        
        activity = ActivityLog(
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            device_id=device_id,
            session_id=session_id,
            access_method=access_method,
            api_key_id=api_key_id,
            mcp_agent_id=mcp_agent_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            details=details or {},
            error_message=error_message
        )
        
        db.add(activity)
        # Don't commit here - let the caller handle the transaction
        
        return activity
        
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        # Don't raise - logging should not break the main flow
        return None