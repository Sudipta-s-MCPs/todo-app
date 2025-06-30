"""
Duplicate task detection service
Created: 2025-01-30 14:27:00 PST
"""

from typing import List, Dict, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from difflib import SequenceMatcher
import re

from app.models.task import Task, TaskStatus
from app.models.workspace import List as TaskList
from app.utils.security import calculate_similarity_hash


class DuplicateDetector:
    """Service for detecting duplicate tasks"""
    
    # Thresholds for similarity
    TITLE_THRESHOLD = 0.8  # 80% similarity
    DESCRIPTION_THRESHOLD = 0.7  # 70% similarity
    COMBINED_THRESHOLD = 0.75  # 75% combined similarity
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common punctuation
        text = re.sub(r'[.,!?;:]', '', text)
        
        return text
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        text1 = DuplicateDetector.normalize_text(text1)
        text2 = DuplicateDetector.normalize_text(text2)
        
        if not text1 or not text2:
            return 0.0
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    @classmethod
    def calculate_task_similarity(
        cls,
        task1_title: str,
        task1_desc: str,
        task2_title: str,
        task2_desc: str
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate overall similarity between two tasks
        Returns: (combined_score, {title_score, desc_score})
        """
        title_score = cls.calculate_similarity(task1_title, task2_title)
        desc_score = cls.calculate_similarity(task1_desc or "", task2_desc or "")
        
        # Weight title more heavily than description
        if task1_desc and task2_desc:
            combined_score = (title_score * 0.7) + (desc_score * 0.3)
        else:
            combined_score = title_score
        
        return combined_score, {
            "title_similarity": title_score,
            "description_similarity": desc_score,
            "combined_similarity": combined_score
        }
    
    @classmethod
    async def find_duplicates(
        cls,
        db: AsyncSession,
        title: str,
        description: str,
        list_id: UUID,
        exclude_task_id: UUID = None
    ) -> List[Tuple[Task, Dict[str, float]]]:
        """
        Find potential duplicate tasks
        Returns list of (task, similarity_scores) tuples
        """
        # Get the workspace_id from the list
        result = await db.execute(
            select(TaskList.workspace_id).where(TaskList.id == list_id)
        )
        workspace_id = result.scalar_one_or_none()
        
        if not workspace_id:
            return []
        
        # First, try to find exact or near-exact matches using similarity hash
        similarity_hash = calculate_similarity_hash(title, description)
        
        # Query for tasks in the same workspace
        query = select(Task).join(
            TaskList, Task.list_id == TaskList.id
        ).where(
            TaskList.workspace_id == workspace_id,
            Task.status != TaskStatus.COMPLETED,
            Task.status != TaskStatus.ARCHIVED
        )
        
        if exclude_task_id:
            query = query.where(Task.id != exclude_task_id)
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        # Calculate similarities
        duplicates = []
        
        for task in tasks:
            combined_score, scores = cls.calculate_task_similarity(
                title, description or "",
                task.title, task.description or ""
            )
            
            # Check if any threshold is met
            if (scores["title_similarity"] >= cls.TITLE_THRESHOLD or
                scores["description_similarity"] >= cls.DESCRIPTION_THRESHOLD or
                combined_score >= cls.COMBINED_THRESHOLD):
                duplicates.append((task, scores))
        
        # Sort by combined similarity score
        duplicates.sort(key=lambda x: x[1]["combined_similarity"], reverse=True)
        
        return duplicates
    
    @classmethod
    async def check_duplicate_on_create(
        cls,
        db: AsyncSession,
        title: str,
        description: str,
        list_id: UUID
    ) -> Tuple[bool, List[Task], Dict[UUID, Dict[str, float]]]:
        """
        Check for duplicates when creating a new task
        Returns: (has_duplicates, duplicate_tasks, similarity_scores_by_task_id)
        """
        duplicates = await cls.find_duplicates(db, title, description, list_id)
        
        if not duplicates:
            return False, [], {}
        
        # Extract tasks and scores
        duplicate_tasks = [task for task, _ in duplicates]
        scores_by_id = {task.id: scores for task, scores in duplicates}
        
        return True, duplicate_tasks, scores_by_id
    
    @classmethod
    async def check_duplicate_on_update(
        cls,
        db: AsyncSession,
        task_id: UUID,
        new_title: str,
        new_description: str,
        list_id: UUID
    ) -> Tuple[bool, List[Task], Dict[UUID, Dict[str, float]]]:
        """
        Check for duplicates when updating an existing task
        Returns: (has_duplicates, duplicate_tasks, similarity_scores_by_task_id)
        """
        duplicates = await cls.find_duplicates(
            db, new_title, new_description, list_id, exclude_task_id=task_id
        )
        
        if not duplicates:
            return False, [], {}
        
        # Extract tasks and scores
        duplicate_tasks = [task for task, _ in duplicates]
        scores_by_id = {task.id: scores for task, scores in duplicates}
        
        return True, duplicate_tasks, scores_by_id