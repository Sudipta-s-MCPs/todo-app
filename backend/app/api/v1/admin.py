"""
Admin API endpoints for user, MCP agent, and API key management
Created: 2025-01-30 19:30:00 PST
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete, update
from sqlalchemy.orm import selectinload, joinedload

from app.database import get_db
from app.models.user import User, UserDevice, APIKey, MCPAgent, AccessMethod
from app.models.workspace import Workspace, WorkspaceMember
from app.models.task import Task
from app.models.activity import ActivityLog, ActionType
from app.models.oauth import OAuthClient, OAuthToken
from app.api.deps import get_current_user, get_current_admin_user, is_admin_user
from app.schemas.auth import UserInfo
from app.schemas.admin import UserAdminCreate, UserAdminUpdate
from app.utils.security import get_password_hash
from app.services.email_service import email_service
import hashlib
import os
import secrets

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_admin_user)) -> User:
    """Dependency to require admin access"""
    return current_user


# User Management Endpoints
@router.post("/users", response_model=Dict[str, Any])
async def create_user(
    user_create: UserAdminCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user"""
    
    # Check if email already exists
    existing = await db.execute(
        select(User).where(User.email == user_create.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_create.email,
        name=user_create.name,
        password_hash=get_password_hash(user_create.password),
        is_active=True,
        is_verified=True,  # Admin-created users are pre-verified
        auth_provider="local"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Add to admin list if needed
    if user_create.is_admin:
        from app.config import settings
        if not settings.ADMIN_USERS:
            settings.ADMIN_USERS = []
        if user_create.email not in settings.ADMIN_USERS:
            settings.ADMIN_USERS.append(user_create.email)
    
    # Log activity
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.REGISTER.value,
        resource_type="user",
        resource_id=str(user.id),
        access_method=AccessMethod.WEB.value,
        details={
            "created_by_admin": True,
            "created_email": user.email,
            "created_name": user.name,
            "is_admin": user_create.is_admin
        }
    )
    db.add(activity)
    await db.commit()
    
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.name,
        "is_active": user.is_active,
        "is_admin": is_admin_user(user),
        "message": "User created successfully"
    }


@router.get("/users", response_model=Dict[str, Any])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all users with pagination and filtering"""
    
    # Base query
    query = select(User).options(
        selectinload(User.devices),
        selectinload(User.api_keys),
        selectinload(User.mcp_agents)
    )
    
    # Apply filters
    if search:
        query = query.where(
            or_(
                User.email.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get additional stats for each user
    user_data = []
    for user in users:
        # Get workspace count
        workspace_count = await db.scalar(
            select(func.count(Workspace.id)).where(
                or_(
                    Workspace.owner_id == user.id,
                    Workspace.id.in_(
                        select(WorkspaceMember.workspace_id).where(
                            WorkspaceMember.user_id == user.id
                        )
                    )
                )
            )
        )
        
        # Get task count
        user_workspaces = await db.execute(
            select(Workspace.id).where(
                or_(
                    Workspace.owner_id == user.id,
                    Workspace.id.in_(
                        select(WorkspaceMember.workspace_id).where(
                            WorkspaceMember.user_id == user.id
                        )
                    )
                )
            )
        )
        workspace_ids = [w[0] for w in user_workspaces]
        
        task_count = 0
        if workspace_ids:
            from app.models.workspace import List
            task_count = await db.scalar(
                select(func.count(Task.id)).where(
                    Task.list_id.in_(
                        select(List.id).where(List.workspace_id.in_(workspace_ids))
                    )
                )
            )
        
        user_dict = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.name,
            "is_active": user.is_active,
            "is_admin": is_admin_user(user),
            "mfa_enabled": user.two_factor_enabled,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_active_at.isoformat() if user.last_active_at else None,
            "workspace_count": workspace_count or 0,
            "task_count": task_count or 0,
            "device_count": len(user.devices),
            "api_key_count": len([k for k in user.api_keys if k.is_active]),
            "mcp_agent_count": len([a for a in user.mcp_agents if a.is_active])
        }
        user_data.append(user_dict)
    
    return {
        "users": user_data,
        "total": total_count or 0,
        "skip": skip,
        "limit": limit
    }


@router.patch("/users/{user_id}/toggle-active", response_model=Dict[str, Any])
async def toggle_user_active_status(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Toggle user active status"""
    
    # Get the user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from deactivating themselves
    if str(user.id) == str(admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Toggle status
    user.is_active = not user.is_active
    await db.commit()
    
    # Log activity
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.USER_UPDATE.value,
        resource_type="user",
        resource_id=str(user.id),
        access_method=AccessMethod.WEB.value,  # Admin panel is web-based
        details={
            "action": "toggle_active",
            "new_status": user.is_active,
            "target_email": user.email
        }
    )
    db.add(activity)
    await db.commit()
    
    return {
        "id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
        "message": f"User {'activated' if user.is_active else 'deactivated'} successfully"
    }


@router.patch("/users/{user_id}/approve", response_model=Dict[str, Any])
async def approve_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Approve a pending user"""
    
    # Get the user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.approval_status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already approved"
        )
    
    # Approve the user
    user.approval_status = "approved"
    user.approved_at = datetime.utcnow()
    user.approved_by = admin.id
    await db.commit()
    
    # Log activity
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.USER_UPDATE.value,
        resource_type="user",
        resource_id=str(user.id),
        access_method=AccessMethod.WEB.value,
        details={
            "action": "approve_user",
            "target_email": user.email
        }
    )
    db.add(activity)
    await db.commit()
    
    # Send approval email
    await email_service.send_approval_email(
        user_email=user.email,
        user_name=user.name,
        approved=True,
        db=db
    )
    
    return {
        "id": str(user.id),
        "email": user.email,
        "approval_status": user.approval_status,
        "message": "User approved successfully"
    }


@router.patch("/users/{user_id}/reject", response_model=Dict[str, Any])
async def reject_user(
    user_id: str,
    rejection_data: Dict[str, str],
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Reject a pending user"""
    
    # Get the user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.approval_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already rejected"
        )
    
    # Reject the user
    user.approval_status = "rejected"
    user.approved_at = datetime.utcnow()
    user.approved_by = admin.id
    user.rejection_reason = rejection_data.get("reason", "Not specified")
    await db.commit()
    
    # Log activity
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.USER_UPDATE.value,
        resource_type="user",
        resource_id=str(user.id),
        access_method=AccessMethod.WEB.value,
        details={
            "action": "reject_user",
            "target_email": user.email,
            "reason": user.rejection_reason
        }
    )
    db.add(activity)
    await db.commit()
    
    # Send rejection email
    await email_service.send_approval_email(
        user_email=user.email,
        user_name=user.name,
        approved=False,
        rejection_reason=user.rejection_reason,
        db=db
    )
    
    return {
        "id": str(user.id),
        "email": user.email,
        "is_approved": user.is_approved,
        "approval_status": user.approval_status,
        "rejection_reason": user.rejection_reason,
        "message": "User rejected"
    }


@router.patch("/users/{user_id}", response_model=Dict[str, Any])
async def update_user(
    user_id: str,
    user_update: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update user details"""
    
    # Get the user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Track changes for activity log
    changes = {}
    
    # Update fields if provided
    if user_update.email is not None and user_update.email != user.email:
        # Check if email is already taken
        existing = await db.execute(
            select(User).where(User.email == user_update.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        changes["email"] = {"old": user.email, "new": user_update.email}
        user.email = user_update.email
    
    if user_update.name is not None and user_update.name != user.name:
        changes["name"] = {"old": user.name, "new": user_update.name}
        user.name = user_update.name
    
    if user_update.is_admin is not None:
        # Handle admin status change
        current_is_admin = is_admin_user(user)
        if user_update.is_admin != current_is_admin:
            if user_update.is_admin:
                # Adding admin - add to ADMIN_USERS in config
                from app.config import settings
                if not settings.ADMIN_USERS:
                    settings.ADMIN_USERS = []
                if user.email not in settings.ADMIN_USERS:
                    settings.ADMIN_USERS.append(user.email)
                changes["admin_status"] = {"old": False, "new": True}
            else:
                # Removing admin - prevent removing self
                if str(user.id) == str(admin.id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot remove your own admin status"
                    )
                # Note: We can't actually remove from settings.ADMIN_USERS at runtime
                # This would need to be done manually in the environment
                changes["admin_status"] = {"old": True, "new": False}
    
    # Save changes
    await db.commit()
    
    # Log activity
    if changes:
        activity = ActivityLog(
            user_id=admin.id,
            action_type=ActionType.USER_UPDATE.value,
            resource_type="user",
            resource_id=str(user.id),
            access_method=AccessMethod.WEB.value,
            details={
                "changes": changes,
                "target_email": user.email
            }
        )
        db.add(activity)
        await db.commit()
    
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.name,
        "is_active": user.is_active,
        "is_admin": is_admin_user(user),
        "message": "User updated successfully"
    }


@router.delete("/users/{user_id}", response_model=Dict[str, str])
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user and all their data"""
    
    # Get the user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from deleting themselves
    if str(user.id) == str(admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Prevent deleting other admins
    if is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users"
        )
    
    # Log activity before deletion
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.USER_DELETE.value,
        resource_type="user",
        resource_id=str(user.id),
        access_method=AccessMethod.WEB.value,  # Admin panel is web-based
        details={
            "deleted_email": user.email,
            "deleted_name": user.name
        }
    )
    db.add(activity)
    
    # Delete user (cascades will handle related data)
    await db.delete(user)
    await db.commit()
    
    return {"message": f"User {user.email} deleted successfully"}


# MCP Agent Management Endpoints
@router.get("/mcp/agents", response_model=Dict[str, Any])
async def get_all_mcp_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all MCP agents across all users"""
    
    # Base query
    query = select(MCPAgent).options(
        joinedload(MCPAgent.user),
        joinedload(MCPAgent.api_key)
    )
    
    # Apply filters
    if is_active is not None:
        query = query.where(MCPAgent.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(MCPAgent.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    agents = result.scalars().all()
    
    # Format response
    agent_data = []
    for agent in agents:
        agent_dict = {
            "id": str(agent.id),
            "agent_name": agent.agent_name,
            "agent_identifier": agent.agent_identifier,
            "capabilities": agent.capabilities,
            "auth_method": agent.auth_method,
            "is_active": agent.is_active,
            "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "user": {
                "id": str(agent.user.id),
                "email": agent.user.email,
                "full_name": agent.user.name
            },
            "api_key": {
                "id": str(agent.api_key.id),
                "name": agent.api_key.name,
                "is_active": agent.api_key.is_active
            } if agent.api_key else None
        }
        agent_data.append(agent_dict)
    
    return {
        "agents": agent_data,
        "total": total_count or 0,
        "skip": skip,
        "limit": limit
    }


@router.delete("/mcp/agents/{agent_id}", response_model=Dict[str, str])
async def delete_mcp_agent(
    agent_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete an MCP agent"""
    
    # Get the agent
    agent = await db.get(MCPAgent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP agent not found"
        )
    
    # Get agent owner info for logging
    owner = await db.get(User, agent.user_id)
    
    # Log activity
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.API_KEY_DELETE.value,
        resource_type="mcp_agent",
        resource_id=str(agent.id),
        access_method=AccessMethod.WEB.value,  # Admin panel is web-based
        details={
            "agent_identifier": agent.agent_identifier,
            "owner_email": owner.email if owner else "unknown"
        }
    )
    db.add(activity)
    
    # Delete agent
    await db.delete(agent)
    await db.commit()
    
    return {"message": f"MCP agent {agent.agent_identifier} deleted successfully"}


@router.post("/mcp/register", response_model=Dict[str, Any])
async def register_mcp_agent_admin(
    request: Dict[str, Any],
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new MCP agent for a user (admin only)
    
    Request body:
    {
        "user_id": "uuid",
        "agent_name": "My MCP Client",
        "description": "Claude Code on MacBook",
        "capabilities": ["task_management", "smart_todo_manager"]
    }
    """
    # Extract request data
    user_id = request.get("user_id")
    agent_name = request.get("agent_name", "MCP Agent")
    description = request.get("description", "")
    capabilities = request.get("capabilities", [
        "task_management",
        "list_management",
        "search",
        "duplicate_detection",
        "smart_todo_manager"
    ])
    
    # Validate user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate unique agent identifier
    import secrets
    agent_identifier = f"mcp_{user_id[:8]}_{secrets.token_hex(8)}"
    
    # Create API key for the agent
    api_key_value = f"mcp_{secrets.token_urlsafe(32)}"
    api_key_hash = hashlib.sha256(api_key_value.encode()).hexdigest()
    
    # Create API key record
    api_key = APIKey(
        user_id=user.id,
        name=f"MCP: {agent_name}",
        key_hash=api_key_hash,
        permissions=["mcp:full"],
        is_active=True
    )
    db.add(api_key)
    
    # Create MCP agent record
    mcp_agent = MCPAgent(
        user_id=user.id,
        agent_name=agent_name,
        agent_identifier=agent_identifier,
        capabilities=capabilities,
        auth_method="api_key",  # This registration creates an API key
        is_active=True
    )
    db.add(mcp_agent)
    
    # Commit to generate IDs
    await db.commit()
    await db.refresh(mcp_agent)
    await db.refresh(api_key)
    
    # Link the API key to the MCP agent
    mcp_agent.api_key_id = api_key.id
    await db.commit()
    
    # Log activity after commit so we have the IDs
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.API_KEY_CREATE.value,
        resource_type="mcp_agent",
        resource_id=str(mcp_agent.id),
        access_method=AccessMethod.WEB.value,
        details={
            "agent_name": agent_name,
            "for_user": user.email,
            "capabilities": capabilities
        }
    )
    db.add(activity)
    await db.commit()
    
    # Generate configurations for different MCP clients
    mcp_endpoint = os.getenv("MCP_ENDPOINT", "http://localhost:5485/mcp")
    
    configurations = {
        "claude_code": {
            "format": "command",
            "content": {
                "command": f"claude mcp add --transport http smart-todo {mcp_endpoint} --header \"X-API-Key: {api_key_value}\" --header \"X-Device-ID: {agent_identifier}\" --header \"X-Device-Name: {agent_name}\" --header \"X-User-ID: {str(user.id)}\"",
                "instructions": [
                    "1. Open your terminal",
                    "2. Run the command below to add the Smart-ToDo MCP server:",
                    "3. Verify connection with: claude mcp list",
                    "4. Check status with: /mcp in Claude Code"
                ]
            }
        },
        "claude_desktop": {
            "format": "remote_integration",
            "content": {
                "method": "Native Remote MCP Support",
                "endpoint": mcp_endpoint,
                "authentication": {
                    "type": "headers",
                    "headers": {
                        "X-API-Key": api_key_value,
                        "X-Device-ID": agent_identifier,
                        "X-Device-Name": agent_name,
                        "X-User-ID": str(user.id)
                    }
                },
                "instructions": [
                    "Claude Desktop now supports remote MCP servers natively!",
                    "1. Open Claude Desktop",
                    "2. Go to Settings > Integrations",
                    "3. Add a new remote MCP server with the endpoint URL",
                    "4. Configure authentication headers as provided above",
                    "Note: This feature is available for Pro, Max, Teams, and Enterprise users"
                ]
            }
        },
        "vscode": {
            "format": "json",
            "content": {
                "mcp.servers": {
                    "smart-todo": {
                        "command": "npx",
                        "args": [
                            "mcp-remote",
                            mcp_endpoint
                        ],
                        "environment": {
                            "TODO_API_KEY": api_key_value,
                            "TODO_USER_ID": str(user.id),
                            "TODO_DEVICE_ID": agent_identifier,
                            "TODO_DEVICE_NAME": agent_name
                        }
                    }
                },
                "instructions": "Add this to your VS Code settings.json. Requires the MCP extension and Node.js."
            }
        },
        "generic": {
            "format": "json",
            "content": {
                "mcp_endpoint": mcp_endpoint,
                "transport": "http",
                "authentication": {
                    "api_key": api_key_value,
                    "user_id": str(user.id),
                    "device_id": agent_identifier,
                    "device_name": agent_name
                },
                "headers": {
                    "X-API-Key": api_key_value,
                    "X-Device-ID": agent_identifier,
                    "X-Device-Name": agent_name,
                    "X-User-ID": str(user.id)
                }
            }
        }
    }
    
    return {
        "agent": {
            "id": str(mcp_agent.id),
            "agent_identifier": agent_identifier,
            "name": agent_name,
            "description": description,
            "capabilities": capabilities,
            "is_active": True,
            "created_at": mcp_agent.created_at.isoformat()
        },
        "configurations": configurations,
        "message": "MCP agent registered successfully"
    }


@router.get("/mcp/agents/{agent_id}/config", response_model=Dict[str, Any])
async def get_mcp_agent_config(
    agent_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get configuration for an existing MCP agent"""
    
    # Get the agent
    agent = await db.get(MCPAgent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP agent not found"
        )
    
    # Get user
    user = await db.get(User, agent.user_id)
    
    # Note: We can't retrieve the actual API key value after creation
    # This endpoint returns configuration templates with placeholders
    agent_name = agent.agent_name or "MCP Agent"
    
    configurations = {
        "claude_code": {
            "format": "command",
            "content": {
                "command": f"claude mcp add --transport http smart-todo {os.getenv('MCP_ENDPOINT', 'http://localhost:5485/mcp')} --header \"X-API-Key: <YOUR_API_KEY>\" --header \"X-Device-ID: {agent.agent_identifier}\" --header \"X-Device-Name: {agent_name}\" --header \"X-User-ID: {str(user.id)}\"",
                "instructions": [
                    "1. Open your terminal", 
                    "2. Replace <YOUR_API_KEY> with the API key provided during registration",
                    "3. Run the command below to add the Smart-ToDo MCP server:",
                    "4. Verify connection with: claude mcp list",
                    "5. Check status with: /mcp in Claude Code"
                ]
            }
        },
        "claude_desktop": {
            "format": "json",
            "content": {
                "mcpServers": {
                    "smart-todo": {
                        "command": "python",
                        "args": ["-m", "mcp_server.server"],
                        "env": {
                            "TODO_API_KEY": "<YOUR_API_KEY>",
                            "TODO_USER_ID": str(user.id),
                            "TODO_DEVICE_ID": agent.agent_identifier,
                            "TODO_DEVICE_NAME": agent_name
                        }
                    }
                }
            }
        },
        "info": {
            "agent_id": str(agent.id),
            "agent_identifier": agent.agent_identifier,
            "user_email": user.email,
            "created_at": agent.created_at.isoformat(),
            "note": "API key cannot be retrieved after creation. Use the key provided during registration."
        }
    }
    
    return {
        "configurations": configurations
    }


# API Key Management Endpoints
@router.get("/api-keys", response_model=Dict[str, Any])
async def get_all_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all API keys across all users"""
    
    # Base query
    query = select(APIKey).options(
        joinedload(APIKey.user),
        selectinload(APIKey.activities)
    )
    
    # Apply filters
    if is_active is not None:
        query = query.where(APIKey.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(APIKey.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    keys = result.scalars().all()
    
    # Format response
    key_data = []
    for key in keys:
        # Check if this API key is linked to an MCP agent
        mcp_agent = await db.scalar(
            select(MCPAgent).where(MCPAgent.api_key_id == key.id)
        )
        
        key_dict = {
            "id": str(key.id),
            "name": key.name,
            "key_preview": key.key_hash[:8] + "...",  # Show first 8 chars
            "scopes": key.permissions,
            "is_active": key.is_active,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "created_at": key.created_at.isoformat() if key.created_at else None,
            "user": {
                "id": str(key.user.id),
                "email": key.user.email,
                "full_name": key.user.name
            },
            "mcp_agent": {
                "id": str(mcp_agent.id),
                "name": mcp_agent.agent_name,
                "identifier": mcp_agent.agent_identifier
            } if mcp_agent else None
        }
        key_data.append(key_dict)
    
    return {
        "keys": key_data,
        "total": total_count or 0,
        "skip": skip,
        "limit": limit
    }


@router.delete("/api-keys/{key_id}", response_model=Dict[str, str])
async def delete_api_key_admin(
    key_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete any API key (admin only)"""
    
    # Get the key
    api_key = await db.get(APIKey, key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Get key owner info for logging
    owner = await db.get(User, api_key.user_id)
    
    # Log activity
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.API_KEY_DELETE.value,
        resource_type="api_key",
        resource_id=str(api_key.id),
        access_method=AccessMethod.WEB.value,  # Admin panel is web-based
        details={
            "key_name": api_key.name,
            "owner_email": owner.email if owner else "unknown"
        }
    )
    db.add(activity)
    
    # Delete key
    await db.delete(api_key)
    await db.commit()
    
    return {"message": f"API key '{api_key.name}' deleted successfully"}


# Additional Admin Stats
@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_admin_overview(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get overview statistics for admin dashboard"""
    
    # User stats
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(
            User.last_active_at >= datetime.utcnow() - timedelta(days=30)
        )
    )
    
    # Workspace stats
    total_workspaces = await db.scalar(select(func.count(Workspace.id)))
    
    # Task stats
    total_tasks = await db.scalar(select(func.count(Task.id)))
    
    # Activity stats (last 24 hours)
    recent_activities = await db.scalar(
        select(func.count(ActivityLog.id)).where(
            ActivityLog.created_at >= datetime.utcnow() - timedelta(hours=24)
        )
    )
    
    return {
        "users": {
            "total": total_users or 0,
            "active": active_users or 0
        },
        "workspaces": {
            "total": total_workspaces or 0
        },
        "tasks": {
            "total": total_tasks or 0
        },
        "activity": {
            "last_24_hours": recent_activities or 0
        }
    }


# OAuth Client Management Endpoints
@router.get("/oauth/clients", response_model=Dict[str, Any])
async def get_all_oauth_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all OAuth clients with pagination and filtering"""
    
    # Base query
    query = select(OAuthClient).options(
        joinedload(OAuthClient.owner),
        selectinload(OAuthClient.tokens)
    )
    
    # Apply filters
    if search:
        query = query.where(
            or_(
                OAuthClient.client_name.ilike(f"%{search}%"),
                OAuthClient.client_id.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.where(OAuthClient.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(OAuthClient.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    clients = result.scalars().all()
    
    # Format response
    client_data = []
    for client in clients:
        # Count active tokens
        active_tokens = len([t for t in client.tokens if not t.is_revoked])
        
        client_dict = {
            "id": str(client.id),
            "client_id": client.client_id,
            "client_name": client.client_name,
            "client_type": client.client_type,
            "redirect_uris": client.redirect_uris,
            "allowed_scopes": client.allowed_scopes,
            "is_active": client.is_active,
            "created_at": client.created_at.isoformat() if client.created_at else None,
            "active_tokens": active_tokens,
            "owner": {
                "id": str(client.owner.id) if client.owner else None,
                "email": client.owner.email if client.owner else None,
                "full_name": client.owner.name if client.owner else None
            } if client.owner else None
        }
        client_data.append(client_dict)
    
    return {
        "clients": client_data,
        "total": total_count or 0,
        "skip": skip,
        "limit": limit
    }


@router.post("/oauth/clients", response_model=Dict[str, Any])
async def create_oauth_client(
    request: Dict[str, Any],
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new OAuth client
    
    Request body:
    {
        "client_name": "Claude Desktop Integration",
        "client_type": "public",  # or "confidential"
        "redirect_uris": ["http://localhost:*", "claude://oauth/callback"],
        "allowed_scopes": ["read", "write"],
        "owner_user_id": "uuid" (optional)
    }
    """
    # Generate client credentials
    client_id = secrets.token_urlsafe(32)
    client_secret = None
    client_secret_hash = None
    
    if request.get("client_type", "public") == "confidential":
        client_secret = secrets.token_urlsafe(48)
        client_secret_hash = get_password_hash(client_secret)
    
    # Create OAuth client
    oauth_client = OAuthClient(
        client_id=client_id,
        client_secret_hash=client_secret_hash,
        client_name=request.get("client_name", "OAuth Client"),
        client_type=request.get("client_type", "public"),
        redirect_uris=request.get("redirect_uris", []),
        allowed_scopes=request.get("allowed_scopes", ["read", "write"]),
        owner_user_id=request.get("owner_user_id"),
        registration_access_token=secrets.token_urlsafe(32),
        is_active=True
    )
    
    db.add(oauth_client)
    await db.commit()
    await db.refresh(oauth_client)
    
    # Log activity
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.CREATE.value,
        resource_type="oauth_client",
        resource_id=str(oauth_client.id),
        access_method=AccessMethod.WEB.value,
        details={
            "client_name": oauth_client.client_name,
            "client_type": oauth_client.client_type
        }
    )
    db.add(activity)
    await db.commit()
    
    response = {
        "id": str(oauth_client.id),
        "client_id": oauth_client.client_id,
        "client_name": oauth_client.client_name,
        "client_type": oauth_client.client_type,
        "redirect_uris": oauth_client.redirect_uris,
        "allowed_scopes": oauth_client.allowed_scopes,
        "registration_access_token": oauth_client.registration_access_token,
        "created_at": oauth_client.created_at.isoformat()
    }
    
    if client_secret:
        response["client_secret"] = client_secret
        response["note"] = "Save the client_secret securely. It will not be shown again."
    
    return response


@router.patch("/oauth/clients/{client_id}", response_model=Dict[str, Any])
async def update_oauth_client(
    client_id: str,
    update_data: Dict[str, Any],
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update an OAuth client"""
    
    # Get the client
    oauth_client = await db.get(OAuthClient, client_id)
    if not oauth_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth client not found"
        )
    
    # Update allowed fields
    allowed_fields = ["client_name", "redirect_uris", "allowed_scopes", "is_active"]
    for field in allowed_fields:
        if field in update_data:
            setattr(oauth_client, field, update_data[field])
    
    # Update timestamp
    oauth_client.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(oauth_client)
    
    # Log activity
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.UPDATE.value,
        resource_type="oauth_client",
        resource_id=str(oauth_client.id),
        access_method=AccessMethod.WEB.value,
        details={
            "updated_fields": list(update_data.keys()),
            "client_name": oauth_client.client_name
        }
    )
    db.add(activity)
    await db.commit()
    
    return {
        "id": str(oauth_client.id),
        "client_id": oauth_client.client_id,
        "client_name": oauth_client.client_name,
        "client_type": oauth_client.client_type,
        "redirect_uris": oauth_client.redirect_uris,
        "allowed_scopes": oauth_client.allowed_scopes,
        "is_active": oauth_client.is_active,
        "updated_at": oauth_client.updated_at.isoformat()
    }


@router.delete("/oauth/clients/{client_id}", response_model=Dict[str, str])
async def delete_oauth_client(
    client_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete an OAuth client"""
    
    # Get the client
    oauth_client = await db.get(OAuthClient, client_id)
    if not oauth_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth client not found"
        )
    
    # Log activity before deletion
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.DELETE.value,
        resource_type="oauth_client",
        resource_id=str(oauth_client.id),
        access_method=AccessMethod.WEB.value,
        details={
            "client_name": oauth_client.client_name,
            "client_id": oauth_client.client_id
        }
    )
    db.add(activity)
    
    # Delete client (cascades will handle tokens and authorization codes)
    await db.delete(oauth_client)
    await db.commit()
    
    return {"message": f"OAuth client {oauth_client.client_name} deleted successfully"}


@router.get("/oauth/tokens", response_model=Dict[str, Any])
async def get_all_oauth_tokens(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    client_id: Optional[str] = None,
    user_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all OAuth tokens with filtering"""
    
    # Base query
    query = select(OAuthToken).options(
        joinedload(OAuthToken.client),
        joinedload(OAuthToken.user),
        joinedload(OAuthToken.mcp_agent)
    )
    
    # Apply filters
    if client_id:
        query = query.where(OAuthToken.client_id == client_id)
    
    if user_id:
        query = query.where(OAuthToken.user_id == user_id)
    
    if is_active is not None:
        if is_active:
            query = query.where(
                OAuthToken.revoked_at.is_(None),
                OAuthToken.access_token_expires_at > datetime.utcnow()
            )
        else:
            query = query.where(
                or_(
                    OAuthToken.revoked_at.is_not(None),
                    OAuthToken.access_token_expires_at <= datetime.utcnow()
                )
            )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(OAuthToken.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    tokens = result.scalars().all()
    
    # Format response
    token_data = []
    for token in tokens:
        token_dict = {
            "id": str(token.id),
            "client": {
                "id": str(token.client.id),
                "name": token.client.client_name
            },
            "user": {
                "id": str(token.user.id),
                "email": token.user.email,
                "full_name": token.user.name
            },
            "scope": token.scope,
            "device_id": token.device_id,
            "device_name": token.device_name,
            "is_active": not token.is_revoked and not token.is_access_token_expired,
            "is_revoked": token.is_revoked,
            "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
            "created_at": token.created_at.isoformat(),
            "expires_at": token.access_token_expires_at.isoformat(),
            "mcp_agent": {
                "id": str(token.mcp_agent.id),
                "name": token.mcp_agent.name
            } if token.mcp_agent else None
        }
        token_data.append(token_dict)
    
    return {
        "tokens": token_data,
        "total": total_count or 0,
        "skip": skip,
        "limit": limit
    }


@router.post("/oauth/tokens/{token_id}/revoke", response_model=Dict[str, str])
async def revoke_oauth_token(
    token_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Revoke an OAuth token"""
    
    # Get the token
    oauth_token = await db.get(OAuthToken, token_id)
    if not oauth_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth token not found"
        )
    
    if oauth_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is already revoked"
        )
    
    # Revoke the token
    oauth_token.revoke()
    await db.commit()
    
    # Log activity
    activity = ActivityLog(
        user_id=admin.id,
        action_type=ActionType.UPDATE.value,
        resource_type="oauth_token",
        resource_id=str(oauth_token.id),
        access_method=AccessMethod.WEB.value,
        details={
            "action": "revoked",
            "client_id": str(oauth_token.client_id),
            "user_id": str(oauth_token.user_id)
        }
    )
    db.add(activity)
    await db.commit()
    
    return {"message": "OAuth token revoked successfully"}