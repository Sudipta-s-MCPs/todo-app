"""
Semantic search API endpoints
Created: 2025-01-02 11:00:00 PST
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, List as TaskList
from app.models.task import Task
from app.schemas.task import TaskResponse
from app.schemas.semantic_search import (
    SemanticSearchQuery, SemanticSearchResponse, 
    RelatedTasksResponse, WorkspaceInsightsResponse
)
from app.api.deps import get_current_user
from app.services.vector_service import get_vector_service
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/semantic-search", response_model=SemanticSearchResponse)
async def semantic_search(
    search_query: SemanticSearchQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search tasks using semantic similarity"""
    # Verify user has access to workspace if specified
    if search_query.workspace_id:
        workspace = await db.get(Workspace, search_query.workspace_id)
        if not workspace or not workspace.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Check access
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
                detail="Access denied to this workspace"
            )
    
    # Perform semantic search
    try:
        vector_service = get_vector_service()
        vector_results = await vector_service.search_similar_tasks(
            query_text=search_query.query,
            workspace_id=search_query.workspace_id,
            list_id=search_query.list_id,
            user_id=current_user.id if search_query.user_tasks_only else None,
            exclude_task_ids=search_query.exclude_task_ids,
            limit=search_query.limit,
            score_threshold=search_query.min_similarity
        )
        
        # Convert vector results to task responses
        task_responses = []
        similarity_scores = {}
        
        if vector_results:
            task_ids = [UUID(vr[0]["task_id"]) for vr in vector_results]
            
            # Fetch task details
            result = await db.execute(
                select(Task).where(Task.id.in_(task_ids))
            )
            tasks_by_id = {task.id: task for task in result.scalars().all()}
            
            # Build responses maintaining order
            for payload, score in vector_results:
                task_id = UUID(payload["task_id"])
                if task_id in tasks_by_id:
                    task = tasks_by_id[task_id]
                    
                    # Get creator info
                    creator = await db.get(User, task.created_by)
                    
                    # Build response
                    response = TaskResponse.model_validate(task)
                    response.creator_name = creator.name if creator else None
                    
                    task_responses.append(response)
                    similarity_scores[str(task_id)] = score
        
        return SemanticSearchResponse(
            tasks=task_responses,
            similarity_scores=similarity_scores,
            total_found=len(task_responses)
        )
        
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search service temporarily unavailable"
        )


@router.get("/tasks/{task_id}/related", response_model=RelatedTasksResponse)
async def get_related_tasks(
    task_id: UUID,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tasks semantically related to a given task"""
    # Verify task exists and user has access
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Get task's list and workspace
    task_list = await db.get(TaskList, task.list_id)
    if not task_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task list not found"
        )
    
    workspace = await db.get(Workspace, task_list.workspace_id)
    if not workspace or not workspace.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Check access
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
            detail="Access denied to this task"
        )
    
    # Get related tasks
    try:
        vector_service = get_vector_service()
        related_results = await vector_service.get_related_tasks(task_id, limit)
        
        # Convert to task responses
        related_tasks = []
        similarity_scores = {}
        
        if related_results:
            task_ids = [UUID(rr[0]["task_id"]) for rr in related_results]
            
            # Fetch task details
            result = await db.execute(
                select(Task).where(Task.id.in_(task_ids))
            )
            tasks_by_id = {task.id: task for task in result.scalars().all()}
            
            # Build responses
            for payload, score in related_results:
                related_task_id = UUID(payload["task_id"])
                if related_task_id in tasks_by_id:
                    related_task = tasks_by_id[related_task_id]
                    
                    # Get creator info
                    creator = await db.get(User, related_task.created_by)
                    
                    # Build response
                    response = TaskResponse.model_validate(related_task)
                    response.creator_name = creator.name if creator else None
                    
                    related_tasks.append(response)
                    similarity_scores[str(related_task_id)] = score
        
        # Build response for original task
        original_creator = await db.get(User, task.created_by)
        original_response = TaskResponse.model_validate(task)
        original_response.creator_name = original_creator.name if original_creator else None
        
        return RelatedTasksResponse(
            original_task=original_response,
            related_tasks=related_tasks,
            similarity_scores=similarity_scores
        )
        
    except Exception as e:
        logger.error(f"Failed to get related tasks: {str(e)}")
        return RelatedTasksResponse(
            original_task=original_response,
            related_tasks=[],
            similarity_scores={}
        )


@router.get("/workspaces/{workspace_id}/insights", response_model=WorkspaceInsightsResponse)
async def get_workspace_insights(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AI-powered insights about tasks in a workspace"""
    # Verify workspace exists and user has access
    workspace = await db.get(Workspace, workspace_id)
    if not workspace or not workspace.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Check access
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
            detail="Access denied to this workspace"
        )
    
    # Get insights
    try:
        vector_service = get_vector_service()
        insights = await vector_service.get_workspace_insights(workspace_id)
        
        return WorkspaceInsightsResponse(
            workspace_id=workspace_id,
            workspace_name=workspace.name,
            **insights
        )
        
    except Exception as e:
        logger.error(f"Failed to get workspace insights: {str(e)}")
        return WorkspaceInsightsResponse(
            workspace_id=workspace_id,
            workspace_name=workspace.name,
            total_tasks=0,
            priority_distribution={},
            status_distribution={},
            vector_space_utilized=False
        )