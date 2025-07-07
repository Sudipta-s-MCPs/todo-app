"""
AI-Enhanced Duplicate task detection service
Created: 2025-01-02 06:15:00 PST
"""

from typing import List, Dict, Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskStatus
from app.models.workspace import List as TaskList
from app.models.user import User
from app.services.duplicate_detection import DuplicateDetector
from app.services.ai_service import get_ai_service, TaskAnalysis
from app.services.vector_service import get_vector_service
from app.services.dynamic_settings import dynamic_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AIEnhancedDuplicateDetector(DuplicateDetector):
    """Enhanced duplicate detector with AI semantic analysis"""
    
    def __init__(self):
        super().__init__()
        self.ai_service = get_ai_service()
        self.vector_service = get_vector_service()
        self.use_ai = dynamic_settings.ENABLE_AI_DUPLICATE_DETECTION
        self.use_vectors = dynamic_settings.ENABLE_VECTOR_SEARCH
    
    @classmethod
    async def find_duplicates_with_ai(
        cls,
        db: AsyncSession,
        title: str,
        description: str,
        list_id: UUID,
        user_id: UUID,
        exclude_task_id: UUID = None
    ) -> List[Tuple[Task, Dict[str, any], Optional[TaskAnalysis]]]:
        """
        Find potential duplicate tasks with AI analysis
        Returns list of (task, similarity_scores, ai_analysis) tuples
        """
        detector = cls()
        
        # Get workspace_id from list
        result = await db.execute(
            select(TaskList.workspace_id).where(TaskList.id == list_id)
        )
        workspace_id = result.scalar_one_or_none()
        if not workspace_id:
            return []
        
        # Try vector search first if enabled
        vector_candidates = []
        if detector.use_vectors:
            try:
                vector_results = await detector.vector_service.find_duplicates(
                    title=title,
                    description=description,
                    workspace_id=workspace_id,
                    similarity_threshold=0.75
                )
                
                # Convert vector results to task objects
                if vector_results:
                    task_ids = [UUID(vr[0]["task_id"]) for vr in vector_results]
                    result = await db.execute(
                        select(Task)
                        .options(selectinload(Task.list))
                        .where(Task.id.in_(task_ids))
                    )
                    tasks_by_id = {task.id: task for task in result.scalars().all()}
                    
                    for payload, score in vector_results:
                        task_id = UUID(payload["task_id"])
                        if task_id in tasks_by_id:
                            # Convert vector score to similarity scores format
                            scores = {
                                "title_similarity": score,
                                "description_similarity": score,
                                "combined_similarity": score,
                                "vector_score": score
                            }
                            vector_candidates.append((tasks_by_id[task_id], scores))
                
                logger.info(f"Found {len(vector_candidates)} candidates via vector search")
            except Exception as e:
                logger.error(f"Vector search failed, falling back to traditional: {str(e)}")
        
        # If no vector results or vectors disabled, use traditional detection
        if not vector_candidates:
            traditional_duplicates = await cls.find_duplicates(
                db, title, description, list_id, exclude_task_id
            )
            
            if not traditional_duplicates:
                return []
            
            vector_candidates = traditional_duplicates
        
        # If AI is disabled, return results without AI analysis
        if not detector.use_ai:
            return [(task, scores, None) for task, scores in vector_candidates]
        
        # Enhance with AI analysis
        ai_enhanced_results = []
        
        # Prepare task data for AI
        new_task_text = f"{title}. {description or ''}"
        existing_tasks = [
            {
                "id": str(task.id),
                "title": task.title,
                "description": task.description or ""
            }
            for task, _ in traditional_duplicates[:5]  # Limit to top 5 for AI
        ]
        
        try:
            # Get AI analysis
            ai_analysis = await detector.ai_service.analyze_duplicate(
                new_task_text,
                existing_tasks,
                str(user_id)
            )
            
            # Combine results
            for task, scores in traditional_duplicates:
                # Find if this task was analyzed by AI
                task_ai_analysis = None
                if ai_analysis.is_duplicate:
                    # AI thinks there's a duplicate, enhance the scores
                    enhanced_scores = scores.copy()
                    enhanced_scores["ai_confidence"] = ai_analysis.confidence
                    enhanced_scores["ai_reasoning"] = ai_analysis.reasoning
                    
                    # Boost combined score if AI is confident
                    if ai_analysis.confidence > 0.7:
                        enhanced_scores["combined_similarity"] = min(
                            1.0,
                            scores["combined_similarity"] * 1.2
                        )
                    
                    task_ai_analysis = ai_analysis
                    ai_enhanced_results.append((task, enhanced_scores, task_ai_analysis))
                else:
                    # AI doesn't think it's a duplicate, use original scores
                    ai_enhanced_results.append((task, scores, None))
            
            # Sort by combined similarity (including AI boost)
            ai_enhanced_results.sort(
                key=lambda x: x[1].get("combined_similarity", 0),
                reverse=True
            )
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {str(e)}")
            # Fallback to traditional results
            return [(task, scores, None) for task, scores in traditional_duplicates]
        
        return ai_enhanced_results
    
    @classmethod
    async def check_duplicate_on_create_with_ai(
        cls,
        db: AsyncSession,
        title: str,
        description: str,
        list_id: UUID,
        user_id: UUID
    ) -> Tuple[bool, List[Task], Dict[UUID, Dict[str, any]], Optional[TaskAnalysis]]:
        """
        Check for duplicates when creating a new task with AI enhancement
        Returns: (has_duplicates, duplicate_tasks, similarity_scores_by_task_id, ai_analysis)
        """
        duplicates = await cls.find_duplicates_with_ai(
            db, title, description, list_id, user_id
        )
        
        if not duplicates:
            return False, [], {}, None
        
        # Extract enhanced results
        duplicate_tasks = []
        scores_by_id = {}
        best_ai_analysis = None
        
        for task, scores, ai_analysis in duplicates:
            duplicate_tasks.append(task)
            scores_by_id[task.id] = scores
            
            # Keep the most relevant AI analysis
            if ai_analysis and not best_ai_analysis:
                best_ai_analysis = ai_analysis
        
        return True, duplicate_tasks, scores_by_id, best_ai_analysis
    
    @classmethod
    async def suggest_task_action(
        cls,
        new_task_title: str,
        new_task_desc: str,
        duplicate_task: Task,
        ai_analysis: Optional[TaskAnalysis]
    ) -> Dict[str, any]:
        """
        Suggest the best action for handling a duplicate
        """
        if ai_analysis and ai_analysis.suggested_action:
            action = ai_analysis.suggested_action
            reasoning = ai_analysis.reasoning
        else:
            # Fallback logic without AI
            if new_task_title.lower() == duplicate_task.title.lower():
                action = "update_existing"
                reasoning = "Exact title match found"
            else:
                action = "create_new"
                reasoning = "Similar but different enough to warrant separate task"
        
        suggestion = {
            "action": action,
            "reasoning": reasoning,
            "duplicate_task_id": str(duplicate_task.id),
            "duplicate_task_title": duplicate_task.title
        }
        
        if action == "update_existing" and ai_analysis:
            if ai_analysis.suggested_title:
                suggestion["suggested_title"] = ai_analysis.suggested_title
            suggestion["merge_description"] = cls._merge_descriptions(
                duplicate_task.description,
                new_task_desc
            )
        
        return suggestion
    
    @staticmethod
    def _merge_descriptions(existing_desc: str, new_desc: str) -> str:
        """Merge two descriptions intelligently"""
        if not existing_desc:
            return new_desc
        if not new_desc:
            return existing_desc
        
        # Simple merge - could be enhanced with AI
        if new_desc in existing_desc:
            return existing_desc
        if existing_desc in new_desc:
            return new_desc
        
        return f"{existing_desc}\n\nAdditional details:\n{new_desc}"


# Convenience function for backward compatibility
async def check_duplicate_with_ai(
    db: AsyncSession,
    title: str,
    description: str,
    list_id: UUID,
    user_id: UUID
) -> Tuple[bool, List[Task], Dict[UUID, Dict[str, any]], Optional[TaskAnalysis]]:
    """Check for duplicates using AI-enhanced detection"""
    return await AIEnhancedDuplicateDetector.check_duplicate_on_create_with_ai(
        db, title, description, list_id, user_id
    )