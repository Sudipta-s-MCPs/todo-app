"""Chat service for processing chat messages with hybrid approach."""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.services.ai_service import get_ai_service
from app.services.cache import get_redis_client
from app.models.user import User
from app.models.task import Task
from app.models.workspace import Workspace, List
from app.schemas.task import TaskCreate
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat interactions with hybrid approach."""
    
    PATTERN_COMMANDS = {
        # Task creation patterns
        r"^(create|add|new)\s+task\s+(.+)$": "create_task",
        r"^remind\s+me\s+to\s+(.+)$": "create_task",
        r"^todo:\s*(.+)$": "create_task",
        
        # Task listing patterns
        r"^(show|list|get)\s+(my\s+)?(all\s+)?tasks?$": "list_tasks",
        r"^what\s+(tasks?\s+)?do\s+i\s+have\??$": "list_tasks",
        r"^(show|list)\s+tasks?\s+in\s+(.+)$": "list_workspace_tasks",
        
        # Task status updates
        r"^(complete|finish|done)\s+task\s+(.+)$": "complete_task",
        r"^mark\s+(.+)\s+as\s+(complete|done|finished)$": "complete_task",
        
        # Workspace operations
        r"^(show|list)\s+(my\s+)?workspaces?$": "list_workspaces",
        r"^create\s+workspace\s+(.+)$": "create_workspace",
        
        # Help patterns
        r"^(help|what\s+can\s+you\s+do|commands?)$": "show_help",
    }
    
    def __init__(self):
        self.cache = get_redis_client()
        self.conversation_cache_ttl = 3600  # 1 hour
        
    async def process_message(
        self, 
        content: str, 
        user_id: str,
        conversation_id: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process a chat message using hybrid approach."""
        
        # Clean and normalize input
        content = content.strip()
        
        # Check for pattern match first
        command_result = await self._try_pattern_match(content, user_id, db)
        if command_result:
            return {
                "message": {
                    "id": str(uuid.uuid4()),
                    "content": command_result["response"],
                    "sender": "assistant",
                    "timestamp": datetime.now(timezone.utc),
                    "metadata": {
                        "type": command_result.get("type", "success"),
                        "usedAI": False,
                        "action": command_result.get("action")
                    }
                },
                "conversationId": conversation_id or str(uuid.uuid4()),
                "tasks": command_result.get("tasks"),
                "action": command_result.get("action"),
                "usedAI": False
            }
        
        # Use AI for natural language task creation
        if await self._looks_like_task_creation(content):
            ai_result = await self._process_with_ai(content, user_id, db)
            return {
                "message": {
                    "id": str(uuid.uuid4()),
                    "content": ai_result["response"],
                    "sender": "assistant",
                    "timestamp": datetime.now(timezone.utc),
                    "metadata": {
                        "type": ai_result.get("type", "task"),
                        "usedAI": True,
                        "confidence": ai_result.get("confidence"),
                        "action": "create_task"
                    }
                },
                "conversationId": conversation_id or str(uuid.uuid4()),
                "tasks": ai_result.get("tasks"),
                "action": "create_task",
                "usedAI": True
            }
        
        # Default response for unrecognized input
        return {
            "message": {
                "id": str(uuid.uuid4()),
                "content": "I'm not sure what you want me to do. Try saying something like 'create task buy groceries' or 'show my tasks'. Type 'help' for more examples.",
                "sender": "assistant",
                "timestamp": datetime.now(timezone.utc),
                "metadata": {
                    "type": "error",
                    "usedAI": False
                }
            },
            "conversationId": conversation_id or str(uuid.uuid4()),
            "usedAI": False
        }
    
    async def _try_pattern_match(
        self, 
        content: str, 
        user_id: str, 
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Try to match content against command patterns."""
        content_lower = content.lower()
        
        for pattern, action in self.PATTERN_COMMANDS.items():
            match = re.match(pattern, content_lower, re.IGNORECASE)
            if match:
                handler = getattr(self, f"_handle_{action}", None)
                if handler:
                    return await handler(match, user_id, db)
        
        return None
    
    async def _looks_like_task_creation(self, content: str) -> bool:
        """Check if content looks like a natural language task creation."""
        # Keywords that suggest task creation
        task_keywords = [
            "need to", "have to", "should", "must", "remember",
            "don't forget", "make sure", "plan to", "want to",
            "tomorrow", "today", "next week", "by", "deadline",
            "urgent", "important", "asap", "priority"
        ]
        
        content_lower = content.lower()
        
        # Check for task-like keywords
        if any(keyword in content_lower for keyword in task_keywords):
            return True
        
        # Check for imperative mood (starts with verb)
        first_word = content_lower.split()[0] if content.split() else ""
        imperative_verbs = [
            "buy", "get", "call", "email", "send", "write", "read",
            "finish", "complete", "review", "prepare", "schedule",
            "book", "pay", "fix", "clean", "organize", "update"
        ]
        
        if first_word in imperative_verbs:
            return True
        
        return False
    
    async def _process_with_ai(
        self, 
        content: str, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process natural language with AI to create tasks."""
        try:
            # Get user's workspaces for context
            workspaces = await db.execute(
                select(Workspace).where(Workspace.owner_id == user_id)
            )
            workspaces = workspaces.scalars().all()
            
            # Parse task with AI
            parsed = await get_ai_service().parse_task_natural_language(
                content, 
                [(w.id, w.name) for w in workspaces]
            )
            
            if not parsed:
                return {
                    "response": "I couldn't understand that as a task. Could you rephrase it?",
                    "type": "error"
                }
            
            # Create the task
            task_data = TaskCreate(
                title=parsed["title"],
                description=parsed.get("description"),
                workspace_id=parsed["workspace_id"],
                priority=parsed.get("priority", "medium"),
                due_date=parsed.get("due_date"),
                tags=parsed.get("tags", [])
            )
            
            # Get default list for workspace
            default_list = await db.execute(
                select(List).where(
                    and_(
                        List.workspace_id == parsed["workspace_id"],
                        List.is_default == True
                    )
                ).limit(1)
            )
            default_list = default_list.scalar_one_or_none()
            
            if not default_list:
                return {
                    "response": "No default list found in the workspace. Please create a list first.",
                    "type": "error"
                }
            
            # Create task directly
            new_task = Task(
                title=parsed["title"],
                description=parsed.get("description"),
                list_id=default_list.id,
                priority=parsed.get("priority", "medium"),
                status="todo",
                due_date=parsed.get("due_date"),
                position=0,
                created_by=user_id,
                created_via_method="chat_ai",
                task_metadata={"tags": parsed.get("tags", [])}
            )
            
            db.add(new_task)
            await db.commit()
            await db.refresh(new_task)
            
            task = new_task
            
            # Get workspace name
            workspace = next((w for w in workspaces if w.id == task.workspace_id), None)
            workspace_name = workspace.name if workspace else "Personal"
            
            response = f"✅ Created task: \"{task.title}\" in {workspace_name}"
            if task.due_date:
                response += f" (due {task.due_date.strftime('%b %d')})"
            
            return {
                "response": response,
                "type": "task",
                "tasks": [task],
                "confidence": parsed.get("confidence", 0.9)
            }
            
        except Exception as e:
            logger.error(f"AI processing error: {str(e)}")
            return {
                "response": "I had trouble understanding that. Please try rephrasing or use a simple command like 'create task [title]'.",
                "type": "error"
            }
    
    async def _handle_create_task(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle pattern-based task creation."""
        # Extract task title from the match
        if match.lastindex == 2:
            task_title = match.group(2)
        else:
            task_title = match.group(1)
        
        task_title = task_title.strip()
        
        # Get default workspace
        workspace = await db.execute(
            select(Workspace).where(
                and_(
                    Workspace.owner_id == user_id,
                    Workspace.type == "personal"
                )
            ).limit(1)
        )
        workspace = workspace.scalar_one_or_none()
        
        if not workspace:
            return {
                "response": "No workspace found. Please create a workspace first.",
                "type": "error",
                "action": "create_task"
            }
        
        # Create task
        task_data = TaskCreate(
            title=task_title,
            workspace_id=workspace.id,
            priority="medium"
        )
        
        # Get default list for workspace
        default_list = await db.execute(
            select(List).where(
                and_(
                    List.workspace_id == workspace.id,
                    List.is_default == True
                )
            ).limit(1)
        )
        default_list = default_list.scalar_one_or_none()
        
        if not default_list:
            # Create a default list if none exists
            default_list = List(
                workspace_id=workspace.id,
                name="Tasks",
                type="default",
                is_default=True,
                color="#2196F3",
                position=0
            )
            db.add(default_list)
            await db.commit()
            await db.refresh(default_list)
        
        # Create task directly
        task = Task(
            title=task_title,
            list_id=default_list.id,
            priority="medium",
            status="todo",
            position=0,
            created_by=user_id,
            created_via_method="chat_pattern"
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        return {
            "response": f"✅ Created task: \"{task.title}\"",
            "type": "task",
            "action": "create_task",
            "tasks": [task]
        }
    
    async def _handle_list_tasks(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle listing all user tasks."""
        # Get user's tasks
        tasks = await db.execute(
            select(Task).where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"])
                )
            ).order_by(Task.created_at.desc()).limit(10)
        )
        tasks = tasks.scalars().all()
        
        if not tasks:
            return {
                "response": "You don't have any active tasks. Create one by saying 'create task [title]'.",
                "type": "success",
                "action": "list_tasks"
            }
        
        response = "Here are your active tasks:\n\n"
        for i, task in enumerate(tasks, 1):
            status_emoji = "🔄" if task.status == "in_progress" else "📋"
            response += f"{i}. {status_emoji} {task.title}"
            if task.due_date:
                response += f" (due {task.due_date.strftime('%b %d')})"
            response += "\n"
        
        return {
            "response": response,
            "type": "success",
            "action": "list_tasks",
            "tasks": tasks
        }
    
    async def _handle_list_workspaces(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle listing user workspaces."""
        workspaces = await db.execute(
            select(Workspace).where(Workspace.owner_id == user_id)
        )
        workspaces = workspaces.scalars().all()
        
        if not workspaces:
            return {
                "response": "You don't have any workspaces yet.",
                "type": "success",
                "action": "list_workspaces"
            }
        
        response = "Your workspaces:\n\n"
        for ws in workspaces:
            emoji = ws.emoji or "📁"
            response += f"{emoji} {ws.name}"
            if ws.description:
                response += f" - {ws.description}"
            response += "\n"
        
        return {
            "response": response,
            "type": "success",
            "action": "list_workspaces"
        }
    
    async def _handle_show_help(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Show help message."""
        help_text = """Here's what I can help you with:

**Creating Tasks:**
• "Create task buy groceries"
• "Remind me to call John tomorrow"
• "Todo: finish the report"
• Or just type naturally: "I need to pick up dry cleaning"

**Viewing Tasks:**
• "Show my tasks"
• "List all tasks"
• "What do I have to do?"

**Managing Tasks:**
• "Complete task buy groceries"
• "Mark report as done"

**Workspaces:**
• "Show my workspaces"
• "List workspaces"

I use AI to understand natural language for task creation, so feel free to describe your tasks naturally!"""
        
        return {
            "response": help_text,
            "type": "success",
            "action": "show_help"
        }
    
    async def get_ai_usage(self, user_id: str) -> Dict[str, int]:
        """Get AI usage stats for a user."""
        try:
            stats = await get_ai_service().get_usage_stats(user_id)
            return {
                "used": stats.get("total_tokens", 0),
                "limit": settings.USER_MONTHLY_TOKEN_LIMIT
            }
        except Exception as e:
            logger.error(f"Error getting AI usage: {str(e)}")
            return {"used": 0, "limit": settings.USER_MONTHLY_TOKEN_LIMIT}
    
    async def get_conversations(
        self, 
        user_id: str, 
        db: AsyncSession
    ) -> "List[Dict[str, Any]]":
        """Get user's chat conversations."""
        # For now, return empty list as we don't persist conversations
        # This can be implemented later if needed
        return []
    
    async def get_conversation_messages(
        self, 
        conversation_id: str, 
        user_id: str, 
        db: AsyncSession
    ) -> "List[Dict[str, Any]]":
        """Get messages for a conversation."""
        # For now, return empty list as we don't persist messages
        # This can be implemented later if needed
        return []


# Global chat service instance
chat_service = ChatService()