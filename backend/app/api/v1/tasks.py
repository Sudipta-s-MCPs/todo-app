"""
Task management API endpoints
Created: 2025-01-30 14:29:00 PST
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.task import (
    Task, TaskAssignment, TaskModification, TaskComment, TaskAttachment,
    TaskStatus, TaskPriority
)
from app.models.workspace import List as TaskList, Workspace, WorkspaceMember, WorkspaceRole
from app.models.user import User, AccessMethod
from app.models.activity import ActionType, ResourceType
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskAssignmentCreate,
    TaskCommentCreate, TaskCommentResponse, TaskAttachmentResponse,
    TaskMoveRequest, TaskBulkOperation, DuplicateCheckResult,
    TaskSearchQuery
)
from app.api.deps import get_current_user, get_access_info, get_access_info_direct, get_device_info
from app.services.activity import log_activity
from app.services.duplicate_detection import DuplicateDetector
from app.utils.security import calculate_similarity_hash
from app.websockets.notifications import notifications

router = APIRouter()


async def get_task_with_permissions(
    task_id: UUID,
    current_user: User,
    db: AsyncSession,
    required_permission: str = "view"
) -> Task:
    """Get task and verify user has permission to access it"""
    # Get task with list and workspace info
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.list))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Get workspace
    workspace = await db.get(Workspace, task.list.workspace_id)
    if not workspace or not workspace.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Check permissions
    has_permission = False
    
    # Owner has all permissions
    if workspace.owner_id == current_user.id:
        has_permission = True
    else:
        # Check membership
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == current_user.id
            )
        )
        member = result.scalar_one_or_none()
        
        if member:
            if required_permission == "view":
                has_permission = True
            elif required_permission == "edit":
                has_permission = member.role in [WorkspaceRole.MEMBER, WorkspaceRole.ADMIN]
            elif required_permission == "delete":
                has_permission = member.role == WorkspaceRole.ADMIN
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    return task


@router.post("/lists/{list_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    list_id: UUID,
    request: Request,
    task_data: TaskCreate,
    force_create: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task"""
    # Verify list exists and user has access
    result = await db.execute(
        select(TaskList).where(TaskList.id == list_id)
    )
    task_list = result.scalar_one_or_none()
    
    if not task_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="List not found"
        )
    
    # Verify workspace access
    workspace = await db.get(Workspace, task_list.workspace_id)
    if not workspace or not workspace.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Check user permission (must be member or owner)
    can_create = workspace.owner_id == current_user.id
    if not can_create:
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == current_user.id,
                WorkspaceMember.role.in_([WorkspaceRole.MEMBER, WorkspaceRole.ADMIN])
            )
        )
        can_create = result.scalar_one_or_none() is not None
    
    if not can_create:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create tasks in this workspace"
        )
    
    # Check for duplicates if not forcing creation
    if not force_create:
        has_duplicates, duplicate_tasks, scores = await DuplicateDetector.check_duplicate_on_create(
            db, task_data.title, task_data.description, list_id
        )
        
        if has_duplicates:
            # Return duplicate information
            duplicate_responses = []
            for dup_task in duplicate_tasks[:5]:  # Limit to 5 duplicates
                dup_response = TaskResponse.model_validate(dup_task)
                duplicate_responses.append(dup_response)
            
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "Potential duplicate tasks found",
                    "duplicates": [resp.model_dump() for resp in duplicate_responses],
                    "similarity_scores": {str(k): v for k, v in scores.items()}
                }
            )
    
    # Get access info
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    
    # Create task
    task = Task(
        list_id=list_id,
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        due_date=task_data.due_date,
        parent_task_id=task_data.parent_task_id,
        task_metadata=task_data.task_metadata,
        created_by=current_user.id,
        created_via_device_id=device_id,
        created_via_method=access_method,
        created_via_session_id=session_id,
        similarity_hash=calculate_similarity_hash(task_data.title, task_data.description)
    )
    db.add(task)
    await db.flush()
    
    # Handle assignments
    if task_data.assigned_to:
        for user_id in task_data.assigned_to:
            assignment = TaskAssignment(
                task_id=task.id,
                user_id=user_id,
                assigned_by=current_user.id
            )
            db.add(assignment)
    
    # Log activity
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.TASK_CREATE.value,
        resource_type=ResourceType.TASK,
        resource_id=task.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={"title": task.title, "list_id": str(list_id)}
    )
    
    await db.commit()
    await db.refresh(task)
    
    # Send WebSocket notification
    await notifications.notify_task_created(
        task=task,
        workspace_id=workspace.id,
        list_id=list_id,
        created_by=current_user.id,
        device_id=device_id
    )
    
    # Build response
    response = TaskResponse.model_validate(task)
    response.creator_name = current_user.name
    
    return response


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get task details"""
    task = await get_task_with_permissions(task_id, current_user, db)
    
    # Get creator info
    creator = await db.get(User, task.created_by)
    
    # Get assignments
    result = await db.execute(
        select(TaskAssignment, User)
        .join(User, User.id == TaskAssignment.user_id)
        .where(TaskAssignment.task_id == task_id)
    )
    assignments = result.all()
    
    # Get counts
    subtask_count = await db.scalar(
        select(func.count(Task.id)).where(Task.parent_task_id == task_id)
    )
    
    comment_count = await db.scalar(
        select(func.count(TaskComment.id)).where(TaskComment.task_id == task_id)
    )
    
    attachment_count = await db.scalar(
        select(func.count(TaskAttachment.id)).where(TaskAttachment.task_id == task_id)
    )
    
    # Build response
    response = TaskResponse.model_validate(task)
    response.creator_name = creator.name if creator else None
    response.assigned_users = [
        {"id": user.id, "name": user.name, "email": user.email}
        for _, user in assignments
    ]
    response.subtask_count = subtask_count or 0
    response.comment_count = comment_count or 0
    response.attachment_count = attachment_count or 0
    
    return response


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    request: Request,
    task_data: TaskUpdate,
    force_update: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update task"""
    task = await get_task_with_permissions(task_id, current_user, db, "edit")
    
    # Get access info
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    
    # Track modifications
    modifications = []
    
    # Check for duplicates if title or description changed
    if not force_update and (task_data.title or task_data.description):
        new_title = task_data.title or task.title
        new_description = task_data.description if task_data.description is not None else task.description
        
        has_duplicates, duplicate_tasks, scores = await DuplicateDetector.check_duplicate_on_update(
            db, task_id, new_title, new_description, task.list_id
        )
        
        if has_duplicates:
            # Return duplicate information
            duplicate_responses = []
            for dup_task in duplicate_tasks[:5]:
                dup_response = TaskResponse.model_validate(dup_task)
                duplicate_responses.append(dup_response)
            
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "Potential duplicate tasks found",
                    "duplicates": [resp.model_dump() for resp in duplicate_responses],
                    "similarity_scores": {str(k): v for k, v in scores.items()}
                }
            )
    
    # Update fields and track changes
    if task_data.title is not None and task_data.title != task.title:
        modifications.append(TaskModification(
            task_id=task_id,
            field_name="title",
            old_value=task.title,
            new_value=task_data.title,
            modified_by=current_user.id,
            modified_via_device_id=device_id,
            modified_via_method=access_method,
            modified_via_session_id=session_id
        ))
        task.title = task_data.title
        task.similarity_hash = calculate_similarity_hash(task_data.title, task.description)
    
    if task_data.description is not None and task_data.description != task.description:
        modifications.append(TaskModification(
            task_id=task_id,
            field_name="description",
            old_value=task.description,
            new_value=task_data.description,
            modified_by=current_user.id,
            modified_via_device_id=device_id,
            modified_via_method=access_method,
            modified_via_session_id=session_id
        ))
        task.description = task_data.description
        task.similarity_hash = calculate_similarity_hash(task.title, task_data.description)
    
    if task_data.status is not None and task_data.status != task.status:
        modifications.append(TaskModification(
            task_id=task_id,
            field_name="status",
            old_value=task.status,
            new_value=task_data.status,
            modified_by=current_user.id,
            modified_via_device_id=device_id,
            modified_via_method=access_method,
            modified_via_session_id=session_id
        ))
        task.status = task_data.status
        
        # Set completed_at if completing
        if task_data.status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
        elif task.status == TaskStatus.COMPLETED:
            task.completed_at = None
    
    if task_data.priority is not None:
        task.priority = task_data.priority
    
    if task_data.due_date is not None:
        task.due_date = task_data.due_date
    
    if task_data.position is not None:
        task.position = task_data.position
    
    if task_data.task_metadata is not None:
        task.task_metadata = task_data.task_metadata
    
    # Handle list move
    if task_data.list_id is not None and task_data.list_id != task.list_id:
        # Verify new list exists and user has access
        new_list = await db.get(TaskList, task_data.list_id)
        if not new_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target list not found"
            )
        
        # Log move activity
        await log_activity(
            db=db,
            user_id=current_user.id,
            action_type=ActionType.TASK_MOVE.value,
            resource_type=ResourceType.TASK,
            resource_id=task_id,
            device_id=device_id,
            session_id=session_id,
            access_method=access_method,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            details={
                "from_list_id": str(task.list_id),
                "to_list_id": str(task_data.list_id)
            }
        )
        
        task.list_id = task_data.list_id
    
    # Add modifications to database
    for mod in modifications:
        db.add(mod)
    
    # Log update activity
    action_type = ActionType.TASK_COMPLETE if task_data.status == TaskStatus.COMPLETED else ActionType.TASK_UPDATE
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=action_type,
        resource_type=ResourceType.TASK,
        resource_id=task_id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    await db.commit()
    await db.refresh(task)
    
    # Prepare changes for WebSocket notification
    changes = {}
    for mod in modifications:
        changes[mod.field_name] = {
            "old": mod.old_value,
            "new": mod.new_value
        }
    
    # Get workspace ID for notification
    task_list = await db.get(TaskList, task.list_id)
    if task_list and changes:
        await notifications.notify_task_updated(
            task=task,
            workspace_id=task_list.workspace_id,
            list_id=task.list_id,
            updated_by=current_user.id,
            device_id=device_id,
            changes=changes
        )
    
    # Build response
    creator = await db.get(User, task.created_by)
    response = TaskResponse.model_validate(task)
    response.creator_name = creator.name if creator else None
    
    return response


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete task"""
    task = await get_task_with_permissions(task_id, current_user, db, "delete")
    
    # Soft delete by marking as archived
    task.status = TaskStatus.ARCHIVED
    
    # Get access info
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    
    # Log activity
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.TASK_DELETE.value,
        resource_type=ResourceType.TASK,
        resource_id=task_id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    await db.commit()
    
    # Get workspace ID for notification
    task_list = await db.get(TaskList, task.list_id)
    if task_list:
        await notifications.notify_task_deleted(
            task_id=task_id,
            workspace_id=task_list.workspace_id,
            list_id=task.list_id,
            deleted_by=current_user.id,
            device_id=device_id
        )
    
    return {"message": "Task deleted successfully"}


@router.post("/tasks/{task_id}/duplicate-check", response_model=DuplicateCheckResult)
async def check_task_duplicates(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check for duplicate tasks"""
    task = await get_task_with_permissions(task_id, current_user, db)
    
    has_duplicates, duplicate_tasks, scores = await DuplicateDetector.check_duplicate_on_update(
        db, task_id, task.title, task.description, task.list_id
    )
    
    # Build responses
    duplicate_responses = []
    for dup_task in duplicate_tasks[:10]:  # Limit to 10
        creator = await db.get(User, dup_task.created_by)
        response = TaskResponse.model_validate(dup_task)
        response.creator_name = creator.name if creator else None
        duplicate_responses.append(response)
    
    return DuplicateCheckResult(
        has_duplicates=has_duplicates,
        duplicates=duplicate_responses,
        similarity_scores={str(k): v for k, v in scores.items()}
    )


@router.post("/tasks/{task_id}/comments", response_model=TaskCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_task_comment(
    task_id: UUID,
    request: Request,
    comment_data: TaskCommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add comment to task"""
    task = await get_task_with_permissions(task_id, current_user, db, "view")
    
    # Get access info
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    
    # Create comment
    comment = TaskComment(
        task_id=task_id,
        content=comment_data.content,
        created_by=current_user.id,
        created_via_device_id=device_id,
        created_via_method=access_method
    )
    db.add(comment)
    
    # Log activity
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.TASK_COMMENT.value,
        resource_type=ResourceType.COMMENT,
        resource_id=comment.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={"task_id": str(task_id)}
    )
    
    await db.commit()
    await db.refresh(comment)
    
    # Build response
    response = TaskCommentResponse.model_validate(comment)
    response.author_name = current_user.name
    response.author_avatar = current_user.avatar_url
    
    return response


@router.get("/tasks/{task_id}/comments", response_model=List[TaskCommentResponse])
async def list_task_comments(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List task comments"""
    task = await get_task_with_permissions(task_id, current_user, db)
    
    # Get comments with authors
    result = await db.execute(
        select(TaskComment, User)
        .join(User, User.id == TaskComment.created_by)
        .where(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.desc())
    )
    
    comments = []
    for comment, author in result:
        response = TaskCommentResponse.model_validate(comment)
        response.author_name = author.name
        response.author_avatar = author.avatar_url
        comments.append(response)
    
    return comments


@router.get("/lists/{list_id}/tasks", response_model=List[TaskResponse])
async def get_list_tasks(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[List[TaskStatus]] = Query(None),
    priority: Optional[List[TaskPriority]] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get tasks in a specific list"""
    # Verify list exists and user has access
    result = await db.execute(
        select(TaskList).where(TaskList.id == list_id)
    )
    task_list = result.scalar_one_or_none()
    
    if not task_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="List not found"
        )
    
    # Verify workspace access
    workspace = await db.get(Workspace, task_list.workspace_id)
    if not workspace or not workspace.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Check user permission
    has_access = workspace.owner_id == current_user.id
    if not has_access:
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == current_user.id
            )
        )
        has_access = result.scalar_one_or_none() is not None
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this list"
        )
    
    # Build query
    query = select(Task).where(Task.list_id == list_id)
    
    # Apply filters
    if status:
        query = query.where(Task.status.in_(status))
    
    if priority:
        query = query.where(Task.priority.in_(priority))
    
    # Order and paginate
    query = query.order_by(Task.position, Task.created_at.desc())
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    # Build responses
    responses = []
    for task in tasks:
        creator = await db.get(User, task.created_by)
        response = TaskResponse.model_validate(task)
        response.creator_name = creator.name if creator else None
        
        # Get assignments
        result = await db.execute(
            select(TaskAssignment, User)
            .join(User, User.id == TaskAssignment.user_id)
            .where(TaskAssignment.task_id == task.id)
        )
        assignments = result.all()
        response.assigned_users = [
            {"id": user.id, "name": user.name, "email": user.email}
            for _, user in assignments
        ]
        
        responses.append(response)
    
    return responses


@router.post("/tasks/search", response_model=List[TaskResponse])
async def search_tasks(
    search_query: TaskSearchQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search tasks across workspaces"""
    # Build base query
    query = select(Task).join(
        TaskList, Task.list_id == TaskList.id
    ).join(
        Workspace, TaskList.workspace_id == Workspace.id
    )
    
    # Filter by user's workspaces
    workspace_subquery = select(Workspace.id).where(
        or_(
            Workspace.owner_id == current_user.id,
            Workspace.id.in_(
                select(WorkspaceMember.workspace_id).where(
                    WorkspaceMember.user_id == current_user.id
                )
            )
        )
    )
    
    query = query.where(Workspace.id.in_(workspace_subquery))
    
    # Apply filters
    if search_query.workspace_id:
        query = query.where(Workspace.id == search_query.workspace_id)
    
    if search_query.list_ids:
        query = query.where(Task.list_id.in_(search_query.list_ids))
    
    if search_query.status:
        query = query.where(Task.status.in_(search_query.status))
    
    if search_query.priority:
        query = query.where(Task.priority.in_(search_query.priority))
    
    if search_query.created_by:
        query = query.where(Task.created_by == search_query.created_by)
    
    if search_query.due_before:
        query = query.where(Task.due_date <= search_query.due_before)
    
    if search_query.due_after:
        query = query.where(Task.due_date >= search_query.due_after)
    
    if search_query.created_before:
        query = query.where(Task.created_at <= search_query.created_before)
    
    if search_query.created_after:
        query = query.where(Task.created_at >= search_query.created_after)
    
    if search_query.parent_task_id is not None:
        query = query.where(Task.parent_task_id == search_query.parent_task_id)
    
    # Text search
    if search_query.query:
        search_term = f"%{search_query.query}%"
        query = query.where(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term)
            )
        )
    
    # Apply assignee filter
    if search_query.assigned_to:
        query = query.join(
            TaskAssignment, Task.id == TaskAssignment.task_id
        ).where(TaskAssignment.user_id.in_(search_query.assigned_to))
    
    # Apply attachment filter
    if search_query.has_attachments is not None:
        if search_query.has_attachments:
            query = query.join(TaskAttachment, Task.id == TaskAttachment.task_id)
        else:
            query = query.outerjoin(
                TaskAttachment, Task.id == TaskAttachment.task_id
            ).where(TaskAttachment.id.is_(None))
    
    # Order and paginate
    query = query.order_by(desc(Task.updated_at))
    query = query.limit(search_query.limit).offset(search_query.offset)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    # Build responses
    responses = []
    for task in tasks:
        creator = await db.get(User, task.created_by)
        response = TaskResponse.model_validate(task)
        response.creator_name = creator.name if creator else None
        responses.append(response)
    
    return responses