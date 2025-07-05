"""
Vector Database Service using Qdrant
Created: 2025-01-02 08:00:00 PST
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime
import asyncio

from app.utils.logging import get_logger
from app.services.cache import get_redis_client
from app.services.dynamic_settings import dynamic_settings

logger = get_logger(__name__)

# Try to import optional dependencies
try:
    import numpy as np
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct, 
        Filter, FieldCondition, MatchValue,
        SearchRequest, UpdateStatus
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("Qdrant dependencies not available - vector search disabled")


class VectorService:
    """Service for managing task embeddings in Qdrant"""
    
    def __init__(self):
        self.host = dynamic_settings.QDRANT_HOST or "localhost"
        self.port = dynamic_settings.QDRANT_PORT
        self.api_key = dynamic_settings.QDRANT_API_KEY or None
        self.collection_name = dynamic_settings.QDRANT_COLLECTION_NAME
        self.embedding_model_name = dynamic_settings.QDRANT_EMBEDDING_MODEL
        self.hf_provider = None
        self.vector_size = 384  # Default size for all-MiniLM-L6-v2
        
        # Check if dependencies are available
        if not QDRANT_AVAILABLE:
            self.client = None
            logger.warning("Vector service disabled due to missing Qdrant dependencies")
            return
        
        try:
            # Initialize Qdrant client using URL format
            qdrant_url = f"http://{self.host}:{self.port}"
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=self.api_key,
                timeout=10
            )
            
            # Create collection if it doesn't exist
            self._ensure_collection()
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {str(e)}")
            self.client = None
    
    def _ensure_collection(self):
        """Ensure the collection exists with proper configuration"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {str(e)}")
            raise
    
    async def _get_hf_provider(self):
        """Get or initialize HuggingFace provider for embeddings"""
        if self.hf_provider is None:
            from app.services.ai_providers.huggingface_provider import HuggingFaceProvider
            self.hf_provider = HuggingFaceProvider()
            if not await self.hf_provider.initialize():
                logger.error("Failed to initialize HuggingFace provider for embeddings")
                self.hf_provider = None
        return self.hf_provider
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text using HuggingFace API"""
        provider = await self._get_hf_provider()
        if not provider:
            logger.warning("HuggingFace provider not available - returning empty vector")
            logger.info("Please ensure HUGGINGFACE_API_TOKEN is configured in settings")
            return [0.0] * self.vector_size
        
        try:
            embedding = await provider.generate_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding via HuggingFace: {str(e)}")
            logger.info("Check your HuggingFace API token and network connectivity")
            # Return empty vector to allow graceful degradation
            return [0.0] * self.vector_size
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently using HuggingFace API"""
        provider = await self._get_hf_provider()
        if not provider:
            logger.warning("HuggingFace provider not available - returning empty vectors")
            return [[0.0] * self.vector_size for _ in texts]
        
        try:
            embeddings = await provider.generate_embeddings_batch(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings via HuggingFace: {str(e)}")
            return [[0.0] * self.vector_size for _ in texts]
    
    async def upsert_task(
        self, 
        task_id: UUID,
        title: str,
        description: Optional[str],
        workspace_id: UUID,
        list_id: UUID,
        user_id: UUID,
        status: str,
        priority: str,
        tags: Optional[List[str]] = None,
        created_at: Optional[datetime] = None
    ) -> bool:
        """Add or update a task in the vector database"""
        if not self.client:
            logger.warning("Vector service not available - skipping task upsert")
            return False
            
        try:
            # Combine title and description for embedding
            text_content = f"{title}. {description or ''}"
            embedding = await self.generate_embedding(text_content)
            
            # Prepare metadata
            payload = {
                "task_id": str(task_id),
                "title": title,
                "description": description or "",
                "workspace_id": str(workspace_id),
                "list_id": str(list_id),
                "user_id": str(user_id),
                "status": status,
                "priority": priority,
                "tags": tags or [],
                "created_at": created_at.isoformat() if created_at else datetime.utcnow().isoformat(),
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            # Create point
            point = PointStruct(
                id=str(task_id),
                vector=embedding,
                payload=payload
            )
            
            # Upsert to Qdrant
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            return operation_info.status == UpdateStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Failed to upsert task {task_id}: {str(e)}")
            return False
    
    async def search_similar_tasks(
        self,
        query_text: str,
        workspace_id: Optional[UUID] = None,
        list_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        exclude_task_ids: Optional[List[UUID]] = None,
        limit: int = 10,
        score_threshold: float = 0.0
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Search for similar tasks using vector similarity"""
        if not self.client:
            logger.warning("Vector service not available - returning empty results")
            return []
            
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query_text)
            
            # Build filter conditions
            must_conditions = []
            
            if workspace_id:
                must_conditions.append(
                    FieldCondition(
                        key="workspace_id",
                        match=MatchValue(value=str(workspace_id))
                    )
                )
            
            if list_id:
                must_conditions.append(
                    FieldCondition(
                        key="list_id",
                        match=MatchValue(value=str(list_id))
                    )
                )
            
            if user_id:
                must_conditions.append(
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=str(user_id))
                    )
                )
            
            # Exclude completed and archived tasks
            must_conditions.extend([
                FieldCondition(
                    key="status",
                    match=MatchValue(value="todo")
                ),
                FieldCondition(
                    key="status",
                    match=MatchValue(value="in_progress")
                )
            ])
            
            # Build filter
            search_filter = Filter(
                should=must_conditions[-2:]  # OR condition for status
            ) if must_conditions else None
            
            # Perform search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Filter out excluded task IDs and format results
            results = []
            exclude_ids = [str(tid) for tid in (exclude_task_ids or [])]
            
            for point in search_result:
                if point.payload.get("task_id") not in exclude_ids:
                    results.append((point.payload, point.score))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar tasks: {str(e)}")
            return []
    
    async def find_duplicates(
        self,
        title: str,
        description: Optional[str],
        workspace_id: UUID,
        similarity_threshold: float = 0.8
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Find potential duplicate tasks using vector similarity"""
        query_text = f"{title}. {description or ''}"
        
        return await self.search_similar_tasks(
            query_text=query_text,
            workspace_id=workspace_id,
            score_threshold=similarity_threshold,
            limit=5
        )
    
    async def delete_task(self, task_id: UUID) -> bool:
        """Remove a task from the vector database"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[str(task_id)]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {str(e)}")
            return False
    
    async def get_related_tasks(
        self,
        task_id: UUID,
        limit: int = 5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Find tasks related to a given task"""
        try:
            # Get the task's embedding
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[str(task_id)],
                with_vectors=True
            )
            
            if not points:
                return []
            
            task_vector = points[0].vector
            task_payload = points[0].payload
            
            # Search for similar tasks excluding the original
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=task_vector,
                limit=limit + 1,  # +1 to exclude self
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="workspace_id",
                            match=MatchValue(value=task_payload["workspace_id"])
                        )
                    ]
                )
            )
            
            # Format results, excluding the original task
            results = []
            for point in search_result:
                if point.payload.get("task_id") != str(task_id):
                    results.append((point.payload, point.score))
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get related tasks: {str(e)}")
            return []
    
    async def update_embeddings_batch(self, tasks: List[Dict[str, Any]]) -> int:
        """Update embeddings for multiple tasks (for migration)"""
        success_count = 0
        
        for task in tasks:
            success = await self.upsert_task(
                task_id=task["id"],
                title=task["title"],
                description=task.get("description"),
                workspace_id=task["workspace_id"],
                list_id=task["list_id"],
                user_id=task["user_id"],
                status=task["status"],
                priority=task["priority"],
                tags=task.get("tags", []),
                created_at=task.get("created_at")
            )
            if success:
                success_count += 1
        
        logger.info(f"Updated {success_count}/{len(tasks)} task embeddings")
        return success_count
    
    async def get_workspace_insights(self, workspace_id: UUID) -> Dict[str, Any]:
        """Get insights about tasks in a workspace using embeddings"""
        try:
            # This could be extended to cluster tasks, find themes, etc.
            # For now, return basic stats
            points = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="workspace_id",
                            match=MatchValue(value=str(workspace_id))
                        )
                    ]
                ),
                limit=1000
            )[0]
            
            # Basic stats
            total_tasks = len(points)
            priority_dist = {}
            status_dist = {}
            
            for point in points:
                priority = point.payload.get("priority", "medium")
                status = point.payload.get("status", "todo")
                
                priority_dist[priority] = priority_dist.get(priority, 0) + 1
                status_dist[status] = status_dist.get(status, 0) + 1
            
            return {
                "total_tasks": total_tasks,
                "priority_distribution": priority_dist,
                "status_distribution": status_dist,
                "vector_space_utilized": total_tasks > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get workspace insights: {str(e)}")
            return {}


# Singleton instance
_vector_service: Optional[VectorService] = None


def get_vector_service() -> VectorService:
    """Get or create vector service instance"""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service