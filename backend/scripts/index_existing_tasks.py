"""
Script to index existing tasks in Qdrant vector database
Created: 2025-01-02 11:15:00 PST
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_async_session
from app.models.task import Task, TaskStatus
from app.models.workspace import List as TaskList
from app.services.vector_service import get_vector_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def index_all_tasks():
    """Index all active tasks in the vector database"""
    vector_service = get_vector_service()
    
    async with get_async_session() as db:
        # Get all non-archived tasks with their lists
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.list))
            .where(Task.status != TaskStatus.ARCHIVED)
            .order_by(Task.created_at)
        )
        tasks = result.scalars().all()
        
        logger.info(f"Found {len(tasks)} tasks to index")
        
        indexed_count = 0
        failed_count = 0
        
        for i, task in enumerate(tasks, 1):
            try:
                # Get workspace ID from list
                task_list = task.list
                if not task_list:
                    logger.warning(f"Task {task.id} has no list, skipping")
                    failed_count += 1
                    continue
                
                # Index task
                success = await vector_service.upsert_task(
                    task_id=task.id,
                    title=task.title,
                    description=task.description,
                    workspace_id=task_list.workspace_id,
                    list_id=task.list_id,
                    user_id=task.created_by,
                    status=task.status.value,
                    priority=task.priority.value,
                    tags=[],  # TODO: Add tags when implemented
                    created_at=task.created_at
                )
                
                if success:
                    indexed_count += 1
                else:
                    failed_count += 1
                
                # Progress update
                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{len(tasks)} tasks processed")
                    
            except Exception as e:
                logger.error(f"Failed to index task {task.id}: {str(e)}")
                failed_count += 1
        
        logger.info(f"Indexing complete: {indexed_count} successful, {failed_count} failed")
        
        # Get workspace insights to verify
        if indexed_count > 0:
            # Get unique workspace IDs
            workspace_ids = set()
            for task in tasks:
                if task.list:
                    workspace_ids.add(task.list.workspace_id)
            
            logger.info(f"Indexed tasks from {len(workspace_ids)} workspaces")
            
            # Sample insights from first workspace
            if workspace_ids:
                sample_workspace_id = list(workspace_ids)[0]
                insights = await vector_service.get_workspace_insights(sample_workspace_id)
                logger.info(f"Sample workspace insights: {insights}")


async def main():
    """Main function"""
    logger.info("Starting task indexing...")
    
    try:
        await index_all_tasks()
        logger.info("Task indexing completed successfully")
    except Exception as e:
        logger.error(f"Task indexing failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())