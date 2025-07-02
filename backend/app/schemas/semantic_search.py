"""
Semantic search schemas
Created: 2025-01-02 11:05:00 PST
"""

from typing import List, Optional, Dict
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.task import TaskResponse


class SemanticSearchQuery(BaseModel):
    """Semantic search query parameters"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query text")
    workspace_id: Optional[UUID] = Field(None, description="Limit search to specific workspace")
    list_id: Optional[UUID] = Field(None, description="Limit search to specific list")
    user_tasks_only: bool = Field(False, description="Only search user's own tasks")
    exclude_task_ids: Optional[List[UUID]] = Field(default_factory=list, description="Task IDs to exclude")
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")


class SemanticSearchResponse(BaseModel):
    """Semantic search results"""
    tasks: List[TaskResponse]
    similarity_scores: Dict[str, float] = Field(default_factory=dict, description="Task ID to similarity score mapping")
    total_found: int


class RelatedTasksResponse(BaseModel):
    """Related tasks response"""
    original_task: TaskResponse
    related_tasks: List[TaskResponse]
    similarity_scores: Dict[str, float] = Field(default_factory=dict, description="Task ID to similarity score mapping")


class WorkspaceInsightsResponse(BaseModel):
    """Workspace insights from vector analysis"""
    workspace_id: UUID
    workspace_name: str
    total_tasks: int
    priority_distribution: Dict[str, int]
    status_distribution: Dict[str, int]
    vector_space_utilized: bool
    # Future: task clusters, themes, etc.