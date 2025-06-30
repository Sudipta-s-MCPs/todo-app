"""
Workspace management API endpoints
Created: 2025-01-30 14:22:00 PST
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.workspace import Workspace, WorkspaceMember, List, WorkspaceType, WorkspaceRole
from app.models.user import User
from app.models.task import Task
from app.models.activity import ActionType, ResourceType
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse,
    WorkspaceMemberAdd, WorkspaceMemberUpdate, WorkspaceMemberResponse,
    ListCreate, ListUpdate, ListResponse, ListReorder
)
from app.api.deps import get_current_user, get_access_info
from app.services.activity import log_activity

router = APIRouter()


async def get_workspace_with_permissions(
    workspace_id: UUID,
    current_user: User,
    db: AsyncSession,
    required_role: Optional[WorkspaceRole] = None
) -> tuple[Workspace, WorkspaceRole]:
    """Get workspace and verify user permissions"""
    # Get workspace
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.is_active == True
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Check if user is owner
    if workspace.owner_id == current_user.id:
        return workspace, WorkspaceRole.OWNER
    
    # Check membership
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check required role
    if required_role:
        role_hierarchy = {
            WorkspaceRole.VIEWER: 0,
            WorkspaceRole.MEMBER: 1,
            WorkspaceRole.ADMIN: 2,
            WorkspaceRole.OWNER: 3
        }
        
        if role_hierarchy.get(member.role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
    
    return workspace, member.role


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: Request,
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new workspace"""
    # Create workspace
    workspace = Workspace(
        name=workspace_data.name,
        type=workspace_data.type,
        owner_id=current_user.id,
        settings_json=workspace_data.settings
    )
    db.add(workspace)
    await db.flush()
    
    # Create default list
    default_list = List(
        workspace_id=workspace.id,
        name="General",
        type=ListType.DEFAULT,
        is_default=True
    )
    db.add(default_list)
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info(
        request, db=db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.WORKSPACE_CREATE,
        resource_type=ResourceType.WORKSPACE,
        resource_id=workspace.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={"name": workspace_data.name, "type": workspace_data.type}
    )
    
    await db.commit()
    await db.refresh(workspace)
    
    response = WorkspaceResponse.model_validate(workspace)
    response.member_count = 1
    return response


@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all user workspaces"""
    # Get owned workspaces
    owned_query = select(Workspace).where(
        Workspace.owner_id == current_user.id,
        Workspace.is_active == True
    )
    
    # Get member workspaces
    member_query = select(Workspace).join(
        WorkspaceMember,
        WorkspaceMember.workspace_id == Workspace.id
    ).where(
        WorkspaceMember.user_id == current_user.id,
        Workspace.is_active == True
    )
    
    # Combine queries
    result = await db.execute(
        owned_query.union(member_query).order_by(Workspace.created_at.desc())
    )
    workspaces = result.scalars().all()
    
    # Get member counts
    workspace_ids = [w.id for w in workspaces]
    member_counts = {}
    
    if workspace_ids:
        result = await db.execute(
            select(
                WorkspaceMember.workspace_id,
                func.count(WorkspaceMember.user_id).label("count")
            )
            .where(WorkspaceMember.workspace_id.in_(workspace_ids))
            .group_by(WorkspaceMember.workspace_id)
        )
        
        for row in result:
            member_counts[row.workspace_id] = row.count
    
    # Build responses
    responses = []
    for workspace in workspaces:
        response = WorkspaceResponse.model_validate(workspace)
        # Add 1 for owner
        response.member_count = member_counts.get(workspace.id, 0) + 1
        responses.append(response)
    
    return responses


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get workspace details"""
    workspace, role = await get_workspace_with_permissions(
        workspace_id, current_user, db
    )
    
    # Get member count
    result = await db.execute(
        select(func.count(WorkspaceMember.user_id))
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    member_count = result.scalar() or 0
    
    response = WorkspaceResponse.model_validate(workspace)
    response.member_count = member_count + 1  # Add owner
    return response


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    request: Request,
    workspace_data: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update workspace"""
    workspace, role = await get_workspace_with_permissions(
        workspace_id, current_user, db, WorkspaceRole.ADMIN
    )
    
    # Update fields
    if workspace_data.name is not None:
        workspace.name = workspace_data.name
    if workspace_data.settings is not None:
        workspace.settings_json = workspace_data.settings
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info(
        request, db=db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.WORKSPACE_UPDATE,
        resource_type=ResourceType.WORKSPACE,
        resource_id=workspace.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    await db.commit()
    await db.refresh(workspace)
    
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete workspace (owner only)"""
    workspace, role = await get_workspace_with_permissions(
        workspace_id, current_user, db, WorkspaceRole.OWNER
    )
    
    workspace.is_active = False
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info(
        request, db=db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.WORKSPACE_DELETE,
        resource_type=ResourceType.WORKSPACE,
        resource_id=workspace.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    await db.commit()
    
    return {"message": "Workspace deleted successfully"}


# Workspace member endpoints
@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List workspace members"""
    workspace, role = await get_workspace_with_permissions(
        workspace_id, current_user, db
    )
    
    # Get members
    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.joined_at)
    )
    
    members = []
    for member, user in result:
        response = WorkspaceMemberResponse(
            workspace_id=member.workspace_id,
            user_id=member.user_id,
            user_email=user.email,
            user_name=user.name,
            role=member.role,
            permissions_json=member.permissions_json,
            joined_at=member.joined_at,
            invited_by=member.invited_by
        )
        members.append(response)
    
    # Add owner
    owner = await db.get(User, workspace.owner_id)
    if owner:
        owner_response = WorkspaceMemberResponse(
            workspace_id=workspace_id,
            user_id=owner.id,
            user_email=owner.email,
            user_name=owner.name,
            role=WorkspaceRole.OWNER,
            permissions_json={},
            joined_at=workspace.created_at,
            invited_by=None
        )
        members.insert(0, owner_response)
    
    return members


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse)
async def add_workspace_member(
    workspace_id: UUID,
    request: Request,
    member_data: WorkspaceMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add member to workspace"""
    workspace, role = await get_workspace_with_permissions(
        workspace_id, current_user, db, WorkspaceRole.ADMIN
    )
    
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == member_data.user_email)
    )
    new_member_user = result.scalar_one_or_none()
    
    if not new_member_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already member
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == new_member_user.id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member"
        )
    
    # Check if owner
    if workspace.owner_id == new_member_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is the workspace owner"
        )
    
    # Add member
    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=new_member_user.id,
        role=member_data.role,
        permissions_json=member_data.permissions,
        invited_by=current_user.id
    )
    db.add(member)
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info(
        request, db=db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.WORKSPACE_MEMBER_ADD,
        resource_type=ResourceType.WORKSPACE,
        resource_id=workspace_id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={
            "new_member_id": str(new_member_user.id),
            "role": member_data.role
        }
    )
    
    await db.commit()
    await db.refresh(member)
    
    return WorkspaceMemberResponse(
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        user_email=new_member_user.email,
        user_name=new_member_user.name,
        role=member.role,
        permissions_json=member.permissions_json,
        joined_at=member.joined_at,
        invited_by=member.invited_by
    )


# List management endpoints
@router.post("/{workspace_id}/lists", response_model=ListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
    workspace_id: UUID,
    request: Request,
    list_data: ListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new list in workspace"""
    workspace, role = await get_workspace_with_permissions(
        workspace_id, current_user, db, WorkspaceRole.MEMBER
    )
    
    # Create list
    new_list = List(
        workspace_id=workspace_id,
        name=list_data.name,
        color=list_data.color,
        icon=list_data.icon,
        type=list_data.type,
        position=list_data.position,
        settings_json=list_data.settings
    )
    db.add(new_list)
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info(
        request, db=db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.LIST_CREATE,
        resource_type=ResourceType.LIST,
        resource_id=new_list.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={"name": list_data.name, "workspace_id": str(workspace_id)}
    )
    
    await db.commit()
    await db.refresh(new_list)
    
    response = ListResponse.model_validate(new_list)
    response.task_count = 0
    return response


@router.get("/{workspace_id}/lists", response_model=List[ListResponse])
async def list_workspace_lists(
    workspace_id: UUID,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all lists in workspace"""
    workspace, role = await get_workspace_with_permissions(
        workspace_id, current_user, db
    )
    
    # Build query
    query = select(List).where(List.workspace_id == workspace_id)
    
    if not include_archived:
        query = query.where(List.is_archived == False)
    
    query = query.order_by(List.position, List.created_at)
    
    result = await db.execute(query)
    lists = result.scalars().all()
    
    # Get task counts
    list_ids = [l.id for l in lists]
    task_counts = {}
    
    if list_ids:
        result = await db.execute(
            select(
                Task.list_id,
                func.count(Task.id).label("count")
            )
            .where(Task.list_id.in_(list_ids))
            .group_by(Task.list_id)
        )
        
        for row in result:
            task_counts[row.list_id] = row.count
    
    # Build responses
    responses = []
    for lst in lists:
        response = ListResponse.model_validate(lst)
        response.task_count = task_counts.get(lst.id, 0)
        responses.append(response)
    
    return responses