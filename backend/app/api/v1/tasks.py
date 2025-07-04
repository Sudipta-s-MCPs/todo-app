"""
Task management API endpoints
Created: 2025-01-30 14:29:00 PST
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import io
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
    TaskSearchQuery, SmartTaskRecommendation
)
from app.api.deps import get_current_user, get_access_info, get_access_info_direct, get_device_info
from app.services.activity import log_activity
from app.services.duplicate_detection import DuplicateDetector
from app.services.duplicate_detection_ai import AIEnhancedDuplicateDetector, check_duplicate_with_ai
from app.services.vector_service import get_vector_service
from app.utils.security import calculate_similarity_hash
from app.utils.logging import get_logger
from app.websockets.notifications import notifications
from app.services.storage_service import get_storage_service

logger = get_logger(__name__)
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
        # Try AI-enhanced detection first
        try:
            has_duplicates, duplicate_tasks, scores, ai_analysis = await check_duplicate_with_ai(
                db, task_data.title, task_data.description, list_id, current_user.id
            )
        except Exception as e:
            # Fallback to traditional detection
            has_duplicates, duplicate_tasks, scores = await DuplicateDetector.check_duplicate_on_create(
                db, task_data.title, task_data.description, list_id
            )
            ai_analysis = None
        
        if has_duplicates:
            # Return duplicate information with AI suggestions
            duplicate_responses = []
            for dup_task in duplicate_tasks[:5]:  # Limit to 5 duplicates
                dup_response = TaskResponse.model_validate(dup_task)
                duplicate_responses.append(dup_response)
            
            response_content = {
                "detail": "Potential duplicate tasks found",
                "duplicates": [resp.model_dump() for resp in duplicate_responses],
                "similarity_scores": {str(k): v for k, v in scores.items()}
            }
            
            # Add AI suggestions if available
            if ai_analysis:
                response_content["ai_analysis"] = {
                    "suggested_action": ai_analysis.suggested_action,
                    "reasoning": ai_analysis.reasoning,
                    "confidence": ai_analysis.confidence
                }
                
                if ai_analysis.suggested_title:
                    response_content["ai_analysis"]["suggested_title"] = ai_analysis.suggested_title
            
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=response_content
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
    
    # Index in vector database
    try:
        vector_service = get_vector_service()
        await vector_service.upsert_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            workspace_id=workspace.id,
            list_id=list_id,
            user_id=current_user.id,
            status=task.status.value,
            priority=task.priority.value,
            tags=[],  # TODO: Add tags support when implemented
            created_at=task.created_at
        )
    except Exception as e:
        logger.warning(f"Failed to index task in vector DB: {str(e)}")
        # Don't fail the request if vector indexing fails
    
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


@router.get("/tasks/smart-recommendations", response_model=List[SmartTaskRecommendation])
async def get_smart_task_recommendations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=10, le=20)
):
    """
    Get AI-powered smart task recommendations
    
    Combines Qdrant vector search with AI analysis to recommend
    the most important tasks across all workspaces
    """
    from app.services.ai_service import get_ai_service
    from app.schemas.task import SmartTaskRecommendation
    
    try:
        # Get all user's active tasks across all workspaces
        # Build query to get tasks from user's workspaces
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
        
        # Get tasks with eager loading
        query = select(Task).join(
            TaskList, Task.list_id == TaskList.id
        ).join(
            Workspace, TaskList.workspace_id == Workspace.id
        ).where(
            Workspace.id.in_(workspace_subquery),
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
        ).options(
            selectinload(Task.list).selectinload(TaskList.workspace),
            selectinload(Task.assignments).selectinload(TaskAssignment.user)
        )
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        # Convert tasks to dict format for AI service
        task_dicts = []
        for task in tasks:
            task_dict = {
                'id': str(task.id),
                'title': task.title,
                'description': task.description,
                'priority': task.priority.value,
                'status': task.status.value,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'reminder_date': task.reminder_date.isoformat() if task.reminder_date else None,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'list_id': str(task.list_id),
                'workspace_id': str(task.list.workspace_id) if task.list else None
            }
            task_dicts.append(task_dict)
        
        # Get AI service and generate recommendations
        ai_service = get_ai_service()
        recommendations = await ai_service.get_smart_task_recommendations(
            user_id=str(current_user.id),
            all_tasks=task_dicts,
            limit=limit
        )
        
        # Build response objects
        recommendation_responses = []
        for rec in recommendations:
            # Find the full task object
            task_id = rec['task']['id']
            full_task = next((t for t in tasks if str(t.id) == task_id), None)
            
            if full_task:
                # Build TaskResponse
                creator = await db.get(User, full_task.created_by)
                task_response = TaskResponse.model_validate(full_task)
                task_response.creator_name = creator.name if creator else None
                
                # Add workspace and list data
                if full_task.list:
                    task_response.list = full_task.list
                    if full_task.list.workspace:
                        task_response.workspace = full_task.list.workspace
                
                # Add assigned users
                if full_task.assignments:
                    task_response.assigned_users = [
                        {"id": str(a.user.id), "name": a.user.name, "email": a.user.email}
                        for a in full_task.assignments
                    ]
                
                # Create recommendation response
                smart_rec = SmartTaskRecommendation(
                    task=task_response,
                    recommendation_reason=rec['recommendation_reason'],
                    urgency_score=rec['urgency_score'],
                    category=rec['category'],
                    vector_relevance_score=rec.get('vector_relevance_score')
                )
                recommendation_responses.append(smart_rec)
        
        return recommendation_responses
        
    except Exception as e:
        logger.error(f"Failed to get smart recommendations: {str(e)}")
        # Fallback to recent tasks
        query = select(Task).join(
            TaskList, Task.list_id == TaskList.id
        ).join(
            Workspace, TaskList.workspace_id == Workspace.id
        ).where(
            Workspace.id.in_(workspace_subquery),
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
        ).options(
            selectinload(Task.list).selectinload(TaskList.workspace)
        ).order_by(
            Task.created_at.desc()
        ).limit(limit)
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        # Build fallback response
        fallback_responses = []
        for i, task in enumerate(tasks):
            creator = await db.get(User, task.created_by)
            task_response = TaskResponse.model_validate(task)
            task_response.creator_name = creator.name if creator else None
            
            if task.list:
                task_response.list = task.list
                if task.list.workspace:
                    task_response.workspace = task.list.workspace
            
            smart_rec = SmartTaskRecommendation(
                task=task_response,
                recommendation_reason="Recent task requiring attention",
                urgency_score=0.5 - (i * 0.05),  # Decreasing score
                category="recent",
                vector_relevance_score=None
            )
            fallback_responses.append(smart_rec)
        
        return fallback_responses


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
    
    # Update vector database if title or description changed
    if task_data.title is not None or task_data.description is not None:
        try:
            # Get workspace ID for vector update
            task_list = await db.get(TaskList, task.list_id)
            if task_list:
                vector_service = get_vector_service()
                await vector_service.upsert_task(
                    task_id=task.id,
                    title=task.title,
                    description=task.description,
                    workspace_id=task_list.workspace_id,
                    list_id=task.list_id,
                    user_id=current_user.id,
                    status=task.status.value,
                    priority=task.priority.value,
                    tags=[],  # TODO: Add tags support
                    created_at=task.created_at
                )
        except Exception as e:
            logger.warning(f"Failed to update task in vector DB: {str(e)}")
            # Don't fail the request if vector update fails
    
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
    
    # Delete from vector database
    try:
        vector_service = get_vector_service()
        await vector_service.delete_task(task_id)
    except Exception as e:
        logger.warning(f"Failed to delete task from vector DB: {str(e)}")
        # Don't fail the request if vector deletion fails
    
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
    
    # Build query with eager loading
    query = select(Task).where(Task.list_id == list_id).options(
        selectinload(Task.list).selectinload(TaskList.workspace),
        selectinload(Task.assignments).selectinload(TaskAssignment.user)
    )
    
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
    
    # Build responses with workspace and list data
    responses = []
    for task in tasks:
        creator = await db.get(User, task.created_by)
        response = TaskResponse.model_validate(task)
        response.creator_name = creator.name if creator else None
        
        # Add workspace and list data
        response.list = task_list
        response.workspace = workspace
        
        # Add assigned users if already loaded
        if task.assignments:
            response.assigned_users = [
                {"id": str(a.user.id), "name": a.user.name, "email": a.user.email}
                for a in task.assignments
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
    # Build base query with eager loading of relationships
    query = select(Task).join(
        TaskList, Task.list_id == TaskList.id
    ).join(
        Workspace, TaskList.workspace_id == Workspace.id
    ).options(
        selectinload(Task.list).selectinload(TaskList.workspace),
        selectinload(Task.assignments).selectinload(TaskAssignment.user)
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
    
    # Build responses with workspace and list data
    responses = []
    for task in tasks:
        creator = await db.get(User, task.created_by)
        response = TaskResponse.model_validate(task)
        response.creator_name = creator.name if creator else None
        
        # Add workspace and list data
        if task.list:
            response.list = task.list
            if task.list.workspace:
                response.workspace = task.list.workspace
        
        # Add assigned users
        if task.assignments:
            response.assigned_users = [
                {"id": str(a.user.id), "name": a.user.name, "email": a.user.email}
                for a in task.assignments
            ]
        
        responses.append(response)
    
    return responses


@router.post("/tasks/{task_id}/attachments", response_model=TaskAttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_task_attachment(
    task_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload an attachment to a task"""
    # Verify task exists and user has access
    task = await get_task_with_permissions(task_id, current_user, db, "edit")
    
    # Validate file size (max 50MB)
    max_size = 50 * 1024 * 1024  # 50MB
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
        )
    
    # Get access info
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    
    try:
        # Upload to storage
        storage_service = get_storage_service()
        file_data = await file.read()
        file_size = len(file_data)
        
        upload_result = await storage_service.upload_file(
            file_data=io.BytesIO(file_data),
            file_name=file.filename,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            user_id=current_user.id,
            task_id=task_id
        )
        
        # Save attachment record
        attachment = TaskAttachment(
            task_id=task_id,
            filename=file.filename,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            storage_path=upload_result["object_name"],
            storage_etag=upload_result.get("etag"),
            storage_version_id=upload_result.get("version_id"),
            uploaded_by=current_user.id
        )
        db.add(attachment)
        
        # Log activity
        await log_activity(
            db=db,
            user_id=current_user.id,
            action_type=ActionType.TASK_ATTACHMENT_ADD,
            resource_type=ResourceType.ATTACHMENT,
            resource_id=attachment.id,
            device_id=device_id,
            session_id=session_id,
            access_method=access_method,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            details={
                "task_id": str(task_id),
                "filename": file.filename,
                "size": file_size
            }
        )
        
        await db.commit()
        await db.refresh(attachment)
        
        # Build response
        response = TaskAttachmentResponse.model_validate(attachment)
        response.download_url = upload_result["url"]
        response.uploader_name = current_user.name
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to upload attachment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload attachment"
        )


@router.get("/tasks/{task_id}/attachments", response_model=List[TaskAttachmentResponse])
async def list_task_attachments(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all attachments for a task"""
    # Verify task exists and user has access
    task = await get_task_with_permissions(task_id, current_user, db, "view")
    
    # Get attachments with uploader info
    result = await db.execute(
        select(TaskAttachment, User)
        .join(User, User.id == TaskAttachment.uploaded_by)
        .where(TaskAttachment.task_id == task_id)
        .order_by(TaskAttachment.uploaded_at.desc())
    )
    
    storage_service = get_storage_service()
    attachments = []
    
    for attachment, uploader in result:
        response = TaskAttachmentResponse.model_validate(attachment)
        response.uploader_name = uploader.name
        response.download_url = storage_service.get_file_url(attachment.storage_path)
        attachments.append(response)
    
    return attachments


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download an attachment"""
    # Get attachment
    attachment = await db.get(TaskAttachment, attachment_id)
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )
    
    # Verify user has access to the task
    task = await get_task_with_permissions(attachment.task_id, current_user, db, "view")
    
    try:
        # Get file from storage
        storage_service = get_storage_service()
        file_data, metadata = await storage_service.download_file(attachment.storage_path)
        
        # Return file
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=attachment.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename={attachment.filename}",
                "Content-Length": str(len(file_data))
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to download attachment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download attachment"
        )


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an attachment"""
    # Get attachment
    attachment = await db.get(TaskAttachment, attachment_id)
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )
    
    # Verify user has permission (must be uploader or have delete permission on task)
    task = await get_task_with_permissions(attachment.task_id, current_user, db, "view")
    
    can_delete = attachment.uploaded_by == current_user.id
    if not can_delete:
        # Check if user has delete permission on task
        try:
            await get_task_with_permissions(attachment.task_id, current_user, db, "delete")
            can_delete = True
        except:
            pass
    
    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete this attachment"
        )
    
    # Get access info
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    
    try:
        # Delete from storage
        storage_service = get_storage_service()
        await storage_service.delete_file(attachment.storage_path)
        
        # Delete record
        await db.delete(attachment)
        
        # Log activity
        await log_activity(
            db=db,
            user_id=current_user.id,
            action_type=ActionType.TASK_ATTACHMENT_DELETE,
            resource_type=ResourceType.ATTACHMENT,
            resource_id=attachment_id,
            device_id=device_id,
            session_id=session_id,
            access_method=access_method,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            details={
                "task_id": str(attachment.task_id),
                "filename": attachment.filename
            }
        )
        
        await db.commit()
        
        return {"message": "Attachment deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete attachment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete attachment"
        )


