"""
Statistics API endpoints
Created: 2025-01-30 18:55:00 PST
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.user import User, UserDevice, APIKey, MCPAgent
from app.models.workspace import Workspace, WorkspaceMember, List, WorkspaceType
from app.models.task import Task, TaskStatus
from app.models.activity import ActivityLog, ActionType
from app.api.deps import get_current_user, get_current_admin_user, is_admin_user
from app.schemas.auth import UserInfo

router = APIRouter()


@router.get("/users", response_model=Dict[str, Any])
async def get_user_statistics(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user statistics for admin dashboard"""
    
    # Total users
    total_users = await db.scalar(
        select(func.count(User.id))
    )
    
    # Active users (logged in within last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = await db.scalar(
        select(func.count(User.id)).where(
            User.last_active_at >= thirty_days_ago
        )
    )
    
    # New users this week
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    new_users = await db.scalar(
        select(func.count(User.id)).where(
            User.created_at >= one_week_ago
        )
    )
    
    # Users with MFA enabled
    mfa_users = await db.scalar(
        select(func.count(User.id)).where(
            User.two_factor_enabled == True
        )
    )
    
    # Count admin users based on ADMIN_USERS config
    all_users = await db.execute(select(User))
    admin_count = sum(1 for user in all_users.scalars() if is_admin_user(user))
    
    return {
        "total": total_users or 0,
        "active": active_users or 0,
        "inactive": (total_users or 0) - (active_users or 0),
        "new_this_week": new_users or 0,
        "with_mfa": mfa_users or 0,
        "admins": admin_count or 0,
        "regular_users": (total_users or 0) - (admin_count or 0)
    }


@router.get("/tasks", response_model=Dict[str, Any])
async def get_task_statistics(
    days: int = Query(30, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get task statistics for current user or all users (admin)"""
    
    # Base query conditions
    conditions = []
    if not is_admin_user(current_user):
        # For regular users, only show their tasks
        user_workspaces = await db.execute(
            select(Workspace.id).where(
                or_(
                    Workspace.owner_id == current_user.id,
                    Workspace.id.in_(
                        select(WorkspaceMember.workspace_id).where(
                            WorkspaceMember.user_id == current_user.id
                        )
                    )
                )
            )
        )
        workspace_ids = [w[0] for w in user_workspaces]
        
        if workspace_ids:
            conditions.append(
                Task.list_id.in_(
                    select(List.id).where(List.workspace_id.in_(workspace_ids))
                )
            )
    
    # Total tasks
    total_query = select(func.count(Task.id))
    if conditions:
        total_query = total_query.where(and_(*conditions))
    total_tasks = await db.scalar(total_query) or 0
    
    # Tasks by status
    status_counts = {}
    for status in TaskStatus:
        count_query = select(func.count(Task.id)).where(Task.status == status)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count = await db.scalar(count_query) or 0
        status_counts[status.value] = count
    
    # Tasks created in time period
    time_limit = datetime.utcnow() - timedelta(days=days)
    recent_query = select(func.count(Task.id)).where(Task.created_at >= time_limit)
    if conditions:
        recent_query = recent_query.where(and_(*conditions))
    recent_tasks = await db.scalar(recent_query) or 0
    
    # Completion rate
    completed_count = status_counts.get(TaskStatus.COMPLETED.value, 0)
    completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0
    
    # Average tasks per day
    avg_per_day = recent_tasks / days if days > 0 else 0
    
    # Overdue tasks
    overdue_query = select(func.count(Task.id)).where(
        and_(
            Task.due_date < datetime.utcnow(),
            Task.status != TaskStatus.COMPLETED
        )
    )
    if conditions:
        overdue_query = overdue_query.where(and_(*conditions))
    overdue_tasks = await db.scalar(overdue_query) or 0
    
    return {
        "total": total_tasks,
        "by_status": status_counts,
        "completed": completed_count,
        "pending": status_counts.get(TaskStatus.TODO.value, 0) + status_counts.get(TaskStatus.IN_PROGRESS.value, 0),
        "completion_rate": round(completion_rate, 2),
        "created_in_period": recent_tasks,
        "average_per_day": round(avg_per_day, 2),
        "overdue": overdue_tasks,
        "period_days": days
    }


@router.get("/workspaces", response_model=Dict[str, Any])
async def get_workspace_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get workspace statistics"""
    
    if is_admin_user(current_user):
        # Admin sees all workspaces
        total_workspaces = await db.scalar(
            select(func.count(Workspace.id))
        )
        
        # Active workspaces (with recent activity)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_workspaces = await db.scalar(
            select(func.count(func.distinct(Workspace.id))).select_from(Workspace).join(
                List, Workspace.id == List.workspace_id
            ).join(
                Task, List.id == Task.list_id
            ).where(
                Task.updated_at >= thirty_days_ago
            )
        )
        
        # Personal vs shared
        personal_count = await db.scalar(
            select(func.count(Workspace.id)).where(
                Workspace.type == WorkspaceType.PERSONAL
            )
        )
        
        # Average members per workspace
        avg_members_result = await db.execute(
            select(
                func.avg(
                    select(func.count(WorkspaceMember.user_id))
                    .where(WorkspaceMember.workspace_id == Workspace.id)
                    .scalar_subquery()
                )
            ).select_from(Workspace)
        )
        avg_members = avg_members_result.scalar() or 0
        
    else:
        # Regular user sees only their workspaces
        user_workspaces_query = select(Workspace).where(
            or_(
                Workspace.owner_id == current_user.id,
                Workspace.id.in_(
                    select(WorkspaceMember.workspace_id).where(
                        WorkspaceMember.user_id == current_user.id
                    )
                )
            )
        )
        result = await db.execute(user_workspaces_query)
        workspaces = result.scalars().all()
        
        total_workspaces = len(workspaces)
        personal_count = sum(1 for w in workspaces if w.type == WorkspaceType.PERSONAL)
        active_workspaces = total_workspaces  # Simplified for regular users
        avg_members = 0  # Not calculated for regular users
    
    # Lists per workspace
    lists_per_workspace = {}
    if not is_admin_user(current_user):
        for workspace in workspaces:
            list_count = await db.scalar(
                select(func.count(List.id)).where(List.workspace_id == workspace.id)
            )
            lists_per_workspace[str(workspace.id)] = list_count
    
    return {
        "total": total_workspaces or 0,
        "active": active_workspaces or 0,
        "personal": personal_count or 0,
        "shared": (total_workspaces or 0) - (personal_count or 0),
        "average_members": round(float(avg_members), 2) if avg_members else 0,
        "lists_per_workspace": lists_per_workspace if not is_admin_user(current_user) else {},
        "owned_by_user": await db.scalar(
            select(func.count(Workspace.id)).where(
                Workspace.owner_id == current_user.id
            )
        ) or 0
    }


@router.get("/system", response_model=Dict[str, Any])
async def get_system_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide statistics (admin only)"""
    if not is_admin_user(current_user):
        return {"error": "Unauthorized"}
    
    # API Keys
    total_api_keys = await db.scalar(
        select(func.count(APIKey.id))
    )
    active_api_keys = await db.scalar(
        select(func.count(APIKey.id)).where(
            APIKey.is_active == True
        )
    )
    
    # MCP Agents
    total_mcp_agents = await db.scalar(
        select(func.count(MCPAgent.id))
    )
    active_mcp_agents = await db.scalar(
        select(func.count(MCPAgent.id)).where(
            MCPAgent.is_active == True
        )
    )
    
    # Recent activity
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_activities = await db.scalar(
        select(func.count(ActivityLog.id)).where(
            ActivityLog.created_at >= twenty_four_hours_ago
        )
    )
    
    # Device statistics
    total_devices = await db.scalar(
        select(func.count(UserDevice.id))
    )
    trusted_devices = await db.scalar(
        select(func.count(UserDevice.id)).where(
            UserDevice.is_trusted == True
        )
    )
    
    # Activity by type (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    activity_breakdown = {}
    for action_type in ActionType:
        count = await db.scalar(
            select(func.count(ActivityLog.id)).where(
                and_(
                    ActivityLog.action_type == action_type.value,
                    ActivityLog.created_at >= seven_days_ago
                )
            )
        )
        activity_breakdown[action_type.value] = count or 0
    
    return {
        "api_keys": {
            "total": total_api_keys or 0,
            "active": active_api_keys or 0
        },
        "mcp_agents": {
            "total": total_mcp_agents or 0,
            "active": active_mcp_agents or 0
        },
        "devices": {
            "total": total_devices or 0,
            "trusted": trusted_devices or 0
        },
        "activity": {
            "last_24_hours": recent_activities or 0,
            "by_type_7_days": activity_breakdown
        }
    }