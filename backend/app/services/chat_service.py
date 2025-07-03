"""Chat service for processing chat messages with hybrid approach."""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from typing import List as TypingList
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.orm import selectinload

from app.services.ai_service import get_ai_service
from app.services.cache import get_redis_client
from app.models.user import User
from app.models.task import Task
from app.models.workspace import Workspace, List, WorkspaceMember
from app.models.chat import ChatMessage
from app.models.settings import SystemSetting
from app.schemas.task import TaskCreate
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat interactions with hybrid approach."""
    
    PATTERN_COMMANDS = {
        # Task creation patterns - expanded for natural language
        r"^(create|add|new)\s+(a\s+)?task\s+(.+)$": "create_task",
        r"^(create|add|new)\s+(a\s+)?task$": "create_task_prompt",  # Handle "create a task" without title
        r"^remind\s+me\s+to\s+(.+)$": "create_task",
        r"^todo:\s*(.+)$": "create_task",
        r"^task:\s*(.+)$": "create_task",
        r"^i\s+need\s+to\s+(.+)$": "create_task",
        r"^i\s+have\s+to\s+(.+)$": "create_task",
        r"^i\s+must\s+(.+)$": "create_task",
        r"^don'?t\s+forget\s+to\s+(.+)$": "create_task",
        r"^remember\s+to\s+(.+)$": "create_task",
        r"^need\s+to\s+(.+)$": "create_task",
        r"^have\s+to\s+(.+)$": "create_task",
        
        # Task listing patterns
        r"^(show|list|get)\s+(my\s+)?(all\s+)?tasks?$": "list_tasks",
        r"^what\s+(tasks?\s+)?do\s+i\s+have\??$": "list_tasks",
        r"^(show|list)\s+tasks?\s+in\s+(.+)$": "list_workspace_tasks",
        
        # Priority-based task listing
        r"^(show|list|get)\s+(my\s+)?(high|medium|low)\s+priority\s+tasks?$": "list_priority_tasks",
        
        # Date-based task listing
        r"^(what|which|show|list)\s+tasks?\s+(are\s+)?due\s+(today|tomorrow|this\s+week|next\s+week)\??$": "list_due_tasks",
        r"^(what|which|show|list)\s+(is|are)\s+due\s+(today|tomorrow|this\s+week|next\s+week)\??$": "list_due_tasks",
        
        # Task status updates - more flexible patterns
        r"^mark\s+(?:the\s+)?(.+?)(?:\s+task)?\s+as\s+(complete|done|finished)$": "complete_task",
        r"^(complete|finish|done)\s+(?:with\s+)?(?:the\s+)?(?:task\s+)?(.+)$": "complete_task",
        r"^(.+?)(?:\s+task)?\s+is\s+(done|complete|finished|completed)$": "complete_task",
        r"^i(?:'ve|'m)?\s+(?:done|finished|completed)\s+(?:with\s+)?(?:the\s+)?(.+?)(?:\s+task)?$": "complete_task",
        r"^(?:just\s+)?(?:done|finished|completed)\s+(?:with\s+)?(?:the\s+)?(.+?)(?:\s+task)?$": "complete_task",
        r"^check\s+off\s+(?:the\s+)?(.+?)(?:\s+task)?$": "complete_task",
        r"^tick\s+(?:off\s+)?(?:the\s+)?(.+?)(?:\s+task)?$": "complete_task",
        
        # Workspace operations
        r"^(show|list)\s+(my\s+)?workspaces?$": "list_workspaces",
        r"^create\s+workspace\s+(.+)$": "create_workspace",
        
        # Greeting patterns
        r"^(hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening)$": "greeting",
        r"^how\s+are\s+you\??$": "greeting",
        r"^what'?s\s+up\??$": "greeting",
        
        # Help patterns
        r"^(help|what\s+can\s+you\s+do|commands?)$": "show_help",
        r"^show\s+me\s+what\s+you\s+can\s+do$": "show_capabilities",
        r"^what\s+are\s+your\s+capabilities\??$": "show_capabilities",
    }
    
    def __init__(self):
        self.cache = get_redis_client()
        self.conversation_cache_ttl = 3600  # 1 hour
        
    def _serialize_task(self, task: Task) -> Dict[str, Any]:
        """Serialize a task object to dictionary."""
        if isinstance(task, dict):
            # Already serialized
            return task
        
        result = {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat(),
            "list_id": str(task.list_id)
        }
        
        # Add list and workspace names if available (from joined query)
        if hasattr(task, 'list') and task.list:
            result["list_name"] = task.list.name
            if hasattr(task.list, 'workspace') and task.list.workspace:
                result["workspace_name"] = task.list.workspace.name
                result["workspace_id"] = str(task.list.workspace.id)
        
        return result
        
    async def process_message(
        self, 
        content: str, 
        user_id: str,
        conversation_id: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process a chat message using AI-first approach."""
        
        # Clean and normalize input
        content = content.strip()
        
        # Save user message to database
        user_message = ChatMessage(
            user_id=user_id,
            content=content,
            sender="user",
            message_metadata=None
        )
        db.add(user_message)
        await db.commit()
        
        # AI-FIRST APPROACH: Try AI processing for ALL messages
        logger.info(f"Processing message with AI-first approach: '{content}'")
        
        try:
            # Process with AI (includes pattern matching as a tool)
            ai_result = await self._process_with_ai_unified(content, user_id, db)
            
            # Log AI processing result
            if ai_result:
                logger.info(f"AI processing result: success={ai_result.get('success')}, provider={ai_result.get('provider', 'unknown')}")
            else:
                logger.warning("AI processing returned None")
            
            # If AI successfully processed the message
            if ai_result and ai_result.get("success", False):
                # Save assistant response
                assistant_message = ChatMessage(
                    user_id=user_id,
                    content=ai_result["response"],
                    sender="assistant",
                    message_metadata={
                        "type": ai_result.get("type", "success"),
                        "usedAI": True,
                        "confidence": ai_result.get("confidence"),
                        "action": ai_result.get("action"),
                        "provider": ai_result.get("provider", "unknown")
                    }
                )
                db.add(assistant_message)
                await db.commit()
                await db.refresh(assistant_message)
                
                # Clean up old messages
                await self._cleanup_old_messages(user_id, db)
                
                return {
                    "message": {
                        "id": str(assistant_message.id),
                        "content": assistant_message.content,
                        "sender": "assistant",
                        "timestamp": assistant_message.created_at,
                        "metadata": assistant_message.message_metadata
                    },
                    "conversationId": conversation_id or str(uuid.uuid4()),
                    "tasks": [self._serialize_task(t) for t in ai_result.get("tasks", [])] if ai_result.get("tasks") else None,
                    "action": ai_result.get("action"),
                    "usedAI": True,
                    "provider": ai_result.get("provider", "unknown")
                }
            else:
                logger.warning(f"AI processing returned unsuccessful result: {ai_result}")
        except Exception as e:
            logger.error(f"AI processing failed with exception: {str(e)}", exc_info=True)
        
        # FALLBACK: If AI processing failed, try pattern matching
        logger.info("AI processing failed or unavailable, falling back to pattern matching")
        command_result = await self._try_pattern_match(content, user_id, db)
        
        if command_result:
            # Save assistant response
            assistant_message = ChatMessage(
                user_id=user_id,
                content=command_result["response"],
                sender="assistant",
                message_metadata={
                    "type": command_result.get("type", "success"),
                    "usedAI": False,
                    "action": command_result.get("action"),
                    "provider": "pattern_match"
                }
            )
            db.add(assistant_message)
            await db.commit()
            await db.refresh(assistant_message)
            
            # Clean up old messages
            await self._cleanup_old_messages(user_id, db)
            
            return {
                "message": {
                    "id": str(assistant_message.id),
                    "content": assistant_message.content,
                    "sender": "assistant",
                    "timestamp": assistant_message.created_at,
                    "metadata": assistant_message.message_metadata
                },
                "conversationId": conversation_id or str(uuid.uuid4()),
                "tasks": [self._serialize_task(t) for t in command_result.get("tasks", [])] if command_result.get("tasks") else None,
                "action": command_result.get("action"),
                "usedAI": False,
                "provider": "pattern_match"
            }
        
        # FINAL FALLBACK: Default response if nothing worked
        default_content = "I'm not sure what you want me to do. Try saying something like 'create task buy groceries' or 'show my tasks'. Type 'help' for more examples."
        assistant_message = ChatMessage(
            user_id=user_id,
            content=default_content,
            sender="assistant",
            message_metadata={
                "type": "error",
                "usedAI": False,
                "provider": "none"
            }
        )
        db.add(assistant_message)
        await db.commit()
        await db.refresh(assistant_message)
        
        # Clean up old messages
        await self._cleanup_old_messages(user_id, db)
        
        return {
            "message": {
                "id": str(assistant_message.id),
                "content": assistant_message.content,
                "sender": "assistant",
                "timestamp": assistant_message.created_at,
                "metadata": assistant_message.message_metadata
            },
            "conversationId": conversation_id or str(uuid.uuid4()),
            "usedAI": False,
            "provider": "none"
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
    
    async def _handle_create_task(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle pattern-based task creation."""
        # Extract task title from the match based on the pattern
        # Pattern groups vary depending on which pattern matched
        groups = match.groups()
        
        # For patterns like "create [a] task ..." - task title is in last group
        if len(groups) == 3:
            task_title = match.group(3)
        # For patterns like "remind me to ..." or "todo: ..." - task title is in first/only group
        else:
            task_title = match.group(1)
        
        task_title = task_title.strip()
        
        # Get user's workspaces (prefer personal workspace)
        owned_workspaces = await db.execute(
            select(Workspace).where(
                and_(
                    Workspace.owner_id == user_id,
                    Workspace.is_active == True
                )
            )
        )
        owned_workspaces = owned_workspaces.scalars().all()
        
        # Get workspaces where user is a member
        member_workspaces = await db.execute(
            select(Workspace).join(WorkspaceMember).where(
                and_(
                    WorkspaceMember.user_id == user_id,
                    Workspace.is_active == True
                )
            )
        )
        member_workspaces = member_workspaces.scalars().all()
        
        # Combine and find personal workspace first
        all_workspaces = owned_workspaces + member_workspaces
        workspace = next((w for w in all_workspaces if w.type == "personal"), None)
        if not workspace and all_workspaces:
            workspace = all_workspaces[0]
        
        if not workspace:
            return {
                "response": "I can't create a task because you don't have any workspaces yet. Please go to the Workspaces page and create your first workspace.",
                "type": "error",
                "action": "create_task"
            }
        
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
                is_default=True,
                color="#2196F3",
                position=0
            )
            db.add(default_list)
            await db.commit()
            await db.refresh(default_list)
        
        # Note: Workspace extraction from title is now handled by AI
        # This pattern handler is just a simple fallback
        
        # Create task suggestion (not saved to database)
        suggested_task = {
            "title": task_title,
            "description": None,
            "workspace_id": str(workspace.id),
            "workspace_name": workspace.name,
            "list_id": str(default_list.id),
            "priority": "medium",
            "status": "todo",
            "due_date": None,
            "tags": [],
            "suggested": True  # Flag to indicate this is a suggestion
        }
        
        response = f"I'll help you create this task:\n\n"
        response += f"**Task**: {task_title}\n"
        response += f"**Workspace**: {workspace.name}\n"
        response += f"**Priority**: Medium\n"
        response += "\nPlease review and approve this task in the preview panel. You can edit any details before creating it."
        
        return {
            "response": response,
            "type": "task_suggestion",
            "action": "suggest_task",
            "tasks": [suggested_task]
        }
    
    async def _handle_create_task_prompt(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle task creation request without a title."""
        return {
            "response": "Sure! What task would you like to create? Just tell me what you need to do.",
            "type": "prompt",
            "action": "create_task_prompt"
        }
    
    async def _handle_list_tasks(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle listing all user tasks."""
        # Get user's tasks with list and workspace info
        tasks = await db.execute(
            select(Task)
            .join(List, Task.list_id == List.id)
            .join(Workspace, List.workspace_id == Workspace.id)
            .where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"])
                )
            )
            .options(
                # Eager load relationships
                selectinload(Task.list).selectinload(List.workspace)
            )
            .order_by(Task.created_at.desc())
            .limit(10)
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
            priority_emoji = "🔴" if task.priority == "high" else "🟡" if task.priority == "medium" else "🟢"
            
            # Include workspace and list context
            response += f"{i}. {status_emoji} {priority_emoji} **{task.title}**\n"
            if hasattr(task, 'list') and task.list:
                response += f"   📁 {task.list.workspace.name} → {task.list.name}\n"
            if task.due_date:
                response += f"   📅 Due {task.due_date.strftime('%b %d, %Y')}\n"
            response += "\n"
        
        return {
            "response": response,
            "type": "success",
            "action": "list_tasks",
            "tasks": [self._serialize_task(t) for t in tasks]
        }
    
    async def _handle_list_priority_tasks(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle listing tasks by priority."""
        # Extract priority level
        priority = match.group(3) if match.lastindex >= 3 else "high"
        
        # Get user's tasks with specific priority
        tasks = await db.execute(
            select(Task)
            .join(List, Task.list_id == List.id)
            .join(Workspace, List.workspace_id == Workspace.id)
            .where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"]),
                    Task.priority == priority
                )
            )
            .options(
                selectinload(Task.list).selectinload(List.workspace)
            )
            .order_by(Task.created_at.desc())
            .limit(10)
        )
        tasks = tasks.scalars().all()
        
        if not tasks:
            return {
                "response": f"You don't have any {priority} priority tasks.",
                "type": "success",
                "action": "list_priority_tasks"
            }
        
        response = f"Here are your {priority} priority tasks:\n\n"
        for i, task in enumerate(tasks, 1):
            status_emoji = "🔄" if task.status == "in_progress" else "📋"
            priority_emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
            
            response += f"{i}. {status_emoji} {priority_emoji} **{task.title}**\n"
            if hasattr(task, 'list') and task.list:
                response += f"   📁 {task.list.workspace.name} → {task.list.name}\n"
            if task.due_date:
                response += f"   📅 Due {task.due_date.strftime('%b %d, %Y')}\n"
            response += "\n"
        
        return {
            "response": response,
            "type": "success",
            "action": "list_priority_tasks",
            "tasks": [self._serialize_task(t) for t in tasks]
        }
    
    async def _handle_list_due_tasks(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle listing tasks by due date."""
        from datetime import timedelta
        
        # Extract time period
        time_period = match.group(3) if match.lastindex >= 3 else "today"
        
        # Calculate date range
        today = datetime.now().date()
        if time_period == "today":
            start_date = today
            end_date = today
        elif time_period == "tomorrow":
            start_date = today + timedelta(days=1)
            end_date = start_date
        elif "this week" in time_period:
            # Start from today to end of week (Sunday)
            days_until_sunday = 6 - today.weekday()
            end_date = today + timedelta(days=days_until_sunday)
            start_date = today
        elif "next week" in time_period:
            # Next Monday to next Sunday
            days_until_monday = 7 - today.weekday()
            start_date = today + timedelta(days=days_until_monday)
            end_date = start_date + timedelta(days=6)
        else:
            start_date = today
            end_date = today
        
        # Get tasks with due dates in range
        tasks = await db.execute(
            select(Task)
            .join(List, Task.list_id == List.id)
            .join(Workspace, List.workspace_id == Workspace.id)
            .where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"]),
                    Task.due_date.isnot(None),
                    Task.due_date >= start_date,
                    Task.due_date <= end_date
                )
            )
            .options(
                selectinload(Task.list).selectinload(List.workspace)
            )
            .order_by(Task.due_date.asc())
        )
        tasks = tasks.scalars().all()
        
        if not tasks:
            return {
                "response": f"You don't have any tasks due {time_period}.",
                "type": "success",
                "action": "list_due_tasks"
            }
        
        response = f"Tasks due {time_period}:\n\n"
        for i, task in enumerate(tasks, 1):
            status_emoji = "🔄" if task.status == "in_progress" else "📋"
            priority_emoji = "🔴" if task.priority == "high" else "🟡" if task.priority == "medium" else "🟢"
            
            response += f"{i}. {status_emoji} {priority_emoji} **{task.title}**\n"
            if hasattr(task, 'list') and task.list:
                response += f"   📁 {task.list.workspace.name} → {task.list.name}\n"
            response += f"   📅 Due {task.due_date.strftime('%b %d, %Y')}\n\n"
        
        return {
            "response": response,
            "type": "success",
            "action": "list_due_tasks",
            "tasks": [self._serialize_task(t) for t in tasks]
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
    
    async def _handle_list_workspace_tasks(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle listing tasks in a specific workspace."""
        workspace_name = match.group(2).strip()
        
        # Find the workspace
        workspace = await db.execute(
            select(Workspace).where(
                and_(
                    or_(
                        Workspace.owner_id == user_id,
                        Workspace.id.in_(
                            select(WorkspaceMember.workspace_id).where(
                                WorkspaceMember.user_id == user_id
                            )
                        )
                    ),
                    func.lower(Workspace.name) == workspace_name.lower()
                )
            )
        )
        workspace = workspace.scalar_one_or_none()
        
        if not workspace:
            return {
                "response": f"I couldn't find a workspace named '{workspace_name}'.",
                "type": "error",
                "action": "list_workspace_tasks"
            }
        
        # Get tasks in the workspace
        tasks = await db.execute(
            select(Task)
            .join(List, Task.list_id == List.id)
            .join(Workspace, List.workspace_id == Workspace.id)
            .where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"]),
                    Workspace.id == workspace.id
                )
            )
            .options(
                selectinload(Task.list).selectinload(List.workspace)
            )
            .order_by(Task.created_at.desc())
            .limit(20)
        )
        tasks = tasks.scalars().all()
        
        if not tasks:
            return {
                "response": f"You don't have any active tasks in the '{workspace.name}' workspace.",
                "type": "success",
                "action": "list_workspace_tasks"
            }
        
        response = f"Tasks in **{workspace.name}** workspace:\n\n"
        
        # Group tasks by list
        tasks_by_list = {}
        for task in tasks:
            list_name = task.list.name if hasattr(task, 'list') and task.list else "Unknown"
            if list_name not in tasks_by_list:
                tasks_by_list[list_name] = []
            tasks_by_list[list_name].append(task)
        
        # Display tasks grouped by list
        task_num = 1
        for list_name, list_tasks in tasks_by_list.items():
            response += f"📂 **{list_name}**\n"
            for task in list_tasks:
                status_emoji = "🔄" if task.status == "in_progress" else "📋"
                priority_emoji = "🔴" if task.priority == "high" else "🟡" if task.priority == "medium" else "🟢"
                
                response += f"{task_num}. {status_emoji} {priority_emoji} {task.title}"
                if task.due_date:
                    response += f" (due {task.due_date.strftime('%b %d')})"
                response += "\n"
                task_num += 1
            response += "\n"
        
        return {
            "response": response.strip(),
            "type": "success",
            "action": "list_workspace_tasks",
            "tasks": [self._serialize_task(t) for t in tasks]
        }
    
    async def _handle_greeting(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle greeting messages."""
        greeting = match.group(1) if match.lastindex >= 1 else "hi"
        
        # Get user's task count for personalized greeting
        task_count_result = await db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"])
                )
            )
        )
        task_count = task_count_result.scalar() or 0
        
        # Create personalized greeting
        if task_count == 0:
            response = f"Hello! 👋 I'm your Smart ToDo assistant. I see you don't have any tasks yet. Would you like me to help you create your first task? Just tell me what you need to do!"
        elif task_count == 1:
            response = f"Hi there! 👋 You have 1 active task. Would you like to see it or add a new one?"
        else:
            response = f"Hello! 👋 You have {task_count} active tasks. Would you like to see them, add a new task, or need help with something else?"
        
        return {
            "response": response,
            "type": "greeting",
            "action": "greeting"
        }
    
    async def _handle_show_capabilities(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Show capabilities message."""
        capabilities_text = """I'm your Smart ToDo assistant! Here's what I can help you with:

**📝 Task Management:**
• Create tasks - Just say "I need to..." or "remind me to..."
• View your tasks - Ask "show my tasks" or "what do I have to do?"
• Complete tasks - Say "complete task [name]" or "mark [task] as done"
• Filter by priority - Try "show high priority tasks"
• Check due dates - Ask "what's due today?" or "tasks due this week"

**📁 Organization:**
• Create workspaces to organize your tasks
• View tasks in specific workspaces
• Manage multiple task lists

**💬 Natural Conversation:**
• I understand natural language - just talk to me normally!
• I remember our conversation context
• Ask me anything about managing your tasks

Feel free to chat naturally - I'll understand what you need! 😊"""
        
        return {
            "response": capabilities_text,
            "type": "help",
            "action": "show_capabilities"
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
• "Create task buy groceries" or "Create a task to review reports"
• "Add task call John" or "New task finish presentation"
• "Remind me to call John tomorrow"
• "Todo: finish the report" or "Task: prepare meeting notes"
• Or just type naturally: "I need to pick up dry cleaning"

**Viewing Tasks:**
• "Show my tasks" or "List all tasks"
• "What do I have to do?"
• "Show my high priority tasks" (also works with medium/low)
• "What tasks are due today?" (also: tomorrow, this week, next week)

**Managing Tasks:**
• "Complete task buy groceries"
• "Mark report as done"

**Workspaces:**
• "Show my workspaces"
• "List workspaces"

I use AI to understand natural language, but also have pattern matching for common commands to ensure reliability!"""
        
        return {
            "response": help_text,
            "type": "success",
            "action": "show_help"
        }
    
    async def _handle_complete_task(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle pattern-based task completion."""
        # Extract task name from various pattern groups
        # The patterns have different capture group positions
        task_name = None
        
        # Check all groups to find the task name
        groups = match.groups()
        for i, group in enumerate(groups):
            if group and group.strip() and group not in ["complete", "done", "finished", "completed", "task", "as", "with", "the", "off"]:
                task_name = group.strip()
                break
        
        if not task_name:
            return {
                "response": "I need to know which task to complete. Please tell me the task name.",
                "type": "error",
                "action": "complete_task"
            }
        
        # Search for the task
        # First try exact match (case-insensitive)
        task_query = select(Task).join(List).join(Workspace).where(
            and_(
                Task.created_by == user_id,
                Task.status.in_(["todo", "in_progress"]),
                func.lower(Task.title) == task_name.lower()
            )
        ).options(selectinload(Task.list).selectinload(List.workspace))
        
        result = await db.execute(task_query)
        task = result.scalar_one_or_none()
        
        # If no exact match, try partial match
        if not task:
            task_query = select(Task).join(List).join(Workspace).where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"]),
                    func.lower(Task.title).contains(task_name.lower())
                )
            ).options(selectinload(Task.list).selectinload(List.workspace))
            
            result = await db.execute(task_query)
            tasks = result.scalars().all()
            
            if len(tasks) == 0:
                return {
                    "response": f"I couldn't find a task matching '{task_name}'. Please check your task list with 'show my tasks'.",
                    "type": "error",
                    "action": "complete_task"
                }
            elif len(tasks) > 1:
                # Multiple matches - ask for clarification
                response = f"I found multiple tasks matching '{task_name}':\n\n"
                for i, t in enumerate(tasks[:5], 1):  # Show max 5 matches
                    response += f"{i}. {t.title}"
                    if hasattr(t, 'list') and t.list:
                        response += f" (in {t.list.workspace.name} → {t.list.name})"
                    response += "\n"
                response += "\nPlease be more specific about which task you want to complete."
                
                return {
                    "response": response,
                    "type": "clarification",
                    "action": "complete_task",
                    "tasks": [self._serialize_task(t) for t in tasks[:5]]
                }
            else:
                task = tasks[0]
        
        # Mark task as completed
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)
        
        # Generate response
        response = f"✅ Great! I've marked '{task.title}' as completed."
        if hasattr(task, 'list') and task.list:
            response += f"\n📁 {task.list.workspace.name} → {task.list.name}"
        
        # Get remaining task count
        remaining_count_result = await db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"])
                )
            )
        )
        remaining_count = remaining_count_result.scalar() or 0
        
        if remaining_count == 0:
            response += "\n\n🎉 Congratulations! You've completed all your tasks!"
        elif remaining_count == 1:
            response += f"\n\nYou have 1 task remaining. Keep it up!"
        else:
            response += f"\n\nYou have {remaining_count} tasks remaining. Keep going!"
        
        return {
            "response": response,
            "type": "success",
            "action": "complete_task",
            "tasks": [self._serialize_task(task)]
        }
    
    async def get_ai_usage(self, user_id: str) -> Dict[str, int]:
        """Get AI usage stats for a user."""
        try:
            # For now, return mock data since we're using free tier providers
            # In the future, we can implement proper usage tracking
            return {
                "used": 0,
                "limit": 50000  # Daily limit for display purposes
            }
        except Exception as e:
            logger.error(f"Error getting AI usage: {str(e)}")
            return {"used": 0, "limit": 50000}
    
    async def get_conversations(
        self, 
        user_id: str, 
        db: AsyncSession
    ) -> TypingList[Dict[str, Any]]:
        """Get user's chat conversations."""
        # Since we have a single conversation per user, return a single item
        # Get message count for the user
        result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.user_id == user_id)
        )
        message_count = result.scalar() or 0
        
        if message_count == 0:
            return []
        
        # Get the timestamp of the first message
        result = await db.execute(
            select(func.min(ChatMessage.created_at)).where(ChatMessage.user_id == user_id)
        )
        first_message_time = result.scalar()
        
        return [{
            "id": f"chat_{user_id}",
            "title": "Chat History",
            "created_at": first_message_time,
            "updated_at": datetime.utcnow(),
            "message_count": message_count
        }]
    
    async def get_conversation_messages(
        self, 
        conversation_id: str, 
        user_id: str, 
        db: AsyncSession
    ) -> TypingList[Dict[str, Any]]:
        """Get messages for a conversation."""
        # Get the chat history limit from settings
        limit_setting = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "chat_history_limit")
        )
        limit_setting = limit_setting.scalar_one_or_none()
        limit = int(limit_setting.value) if limit_setting else 50
        
        # Get the latest messages for the user
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        
        # Return messages in chronological order
        return [
            {
                "id": str(msg.id),
                "content": msg.content,
                "sender": msg.sender,
                "timestamp": msg.created_at,
                "metadata": msg.message_metadata
            }
            for msg in reversed(messages)
        ]
    
    async def _process_with_ai_unified(
        self, 
        content: str, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process message with AI using centralized AI service."""
        try:
            # Get user's context (workspaces, lists, tasks)
            context = await self._get_user_context(user_id, db)
            
            # Get recent chat history for conversational context
            chat_history = await self._get_chat_history(user_id, db, limit=10)
            
            # Use centralized AI service
            ai_service = get_ai_service()
            ai_response = await ai_service.process_conversation(
                message=content,
                user_context=context,
                conversation_history=chat_history,
                mode="chat",
                user_id=user_id
            )
            
            logger.info(f"AI response: intent={ai_response.intent}, use_pattern={ai_response.use_pattern}, provider={ai_response.provider_used}")
            
            # Process AI response
            if ai_response.use_pattern and ai_response.pattern_command:
                # AI decided to use pattern matching
                logger.info(f"AI decided to use pattern matching: {ai_response.pattern_command}")
                pattern_result = await self._execute_pattern_command(
                    ai_response.pattern_command, user_id, db
                )
                if pattern_result:
                    return {
                        "success": True,
                        "response": pattern_result["response"],
                        "type": pattern_result.get("type", "success"),
                        "action": pattern_result.get("action"),
                        "tasks": pattern_result.get("tasks"),
                        "confidence": ai_response.confidence,
                        "provider": ai_response.provider_used
                    }
            
            elif ai_response.intent == "task_creation" and ai_response.task_details:
                # AI wants to create a task
                logger.info(f"AI wants to create task: {ai_response.task_details}")
                task_result = await self._create_task_from_ai(
                    ai_response.task_details, user_id, db
                )
                return {
                    "success": True,
                    "response": ai_response.response,
                    "type": "task_suggestion",
                    "action": "suggest_task",
                    "tasks": [task_result] if task_result else None,
                    "confidence": ai_response.confidence,
                    "provider": ai_response.provider_used
                }
            
            else:
                # General response
                logger.info(f"AI provided general response")
                return {
                    "success": True,
                    "response": ai_response.response,
                    "type": "success",
                    "action": "response",
                    "confidence": ai_response.confidence,
                    "provider": ai_response.provider_used
                }
            
        except Exception as e:
            logger.error(f"AI unified processing error: {str(e)}")
            return {"success": False}
    
    async def _get_chat_history(self, user_id: str, db: AsyncSession, limit: int = 10) -> TypingList[Dict[str, Any]]:
        """Get recent chat history for conversational context."""
        # Get the last N messages for the user
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        
        # Return messages in chronological order
        return [
            {
                "role": "user" if msg.sender == "user" else "assistant",
                "content": msg.content,
                "timestamp": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in reversed(messages)
        ]
    
    async def _get_user_context(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get user's context for AI processing."""
        # Get workspaces
        owned_workspaces = await db.execute(
            select(Workspace).where(
                and_(
                    Workspace.owner_id == user_id,
                    Workspace.is_active == True
                )
            )
        )
        owned_workspaces = owned_workspaces.scalars().all()
        
        member_workspaces = await db.execute(
            select(Workspace).join(WorkspaceMember).where(
                and_(
                    WorkspaceMember.user_id == user_id,
                    Workspace.is_active == True
                )
            )
        )
        member_workspaces = member_workspaces.scalars().all()
        
        workspace_dict = {w.id: w for w in owned_workspaces}
        for w in member_workspaces:
            workspace_dict[w.id] = w
        workspaces = list(workspace_dict.values())
        
        # Get lists
        lists = []
        for workspace in workspaces:
            workspace_lists = await db.execute(
                select(List).where(List.workspace_id == workspace.id)
            )
            for lst in workspace_lists.scalars():
                lists.append({
                    "id": str(lst.id),
                    "name": lst.name,
                    "workspace_id": str(workspace.id),
                    "workspace_name": workspace.name
                })
        
        # Count active tasks
        task_count_result = await db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"])
                )
            )
        )
        task_count = task_count_result.scalar() or 0
        
        return {
            "workspaces": [{"id": str(w.id), "name": w.name} for w in workspaces],
            "lists": lists,
            "task_count": task_count
        }
    
    async def _execute_pattern_command(
        self, 
        command: str, 
        user_id: str, 
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Execute a pattern command directly."""
        # Try to match the command against patterns
        for pattern, handler_name in self.PATTERN_COMMANDS.items():
            match = re.match(pattern, command.lower().strip())
            if match:
                handler = getattr(self, f"_handle_{handler_name}", None)
                if handler:
                    return await handler(match, user_id, db)
        return None
    
    async def _create_task_from_ai(
        self, 
        task_details: Dict[str, Any], 
        user_id: str, 
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Create a task suggestion from AI-extracted details."""
        try:
            workspace_name = None
            list_name = None
            
            # Get workspace name if workspace_id is provided
            if task_details.get("workspace_id"):
                ws_result = await db.execute(
                    select(Workspace).where(
                        and_(
                            Workspace.id == task_details["workspace_id"],
                            or_(
                                Workspace.owner_id == user_id,
                                Workspace.id.in_(
                                    select(WorkspaceMember.workspace_id).where(
                                        WorkspaceMember.user_id == user_id
                                    )
                                )
                            )
                        )
                    )
                )
                workspace = ws_result.scalar_one_or_none()
                if workspace:
                    workspace_name = workspace.name
                else:
                    logger.warning(f"Invalid workspace ID: {task_details['workspace_id']}")
            
            # Validate list and get list name
            if task_details.get("list_id"):
                # Verify list exists and user has access
                list_result = await db.execute(
                    select(List).join(Workspace).where(
                        and_(
                            List.id == task_details["list_id"],
                            or_(
                                Workspace.owner_id == user_id,
                                Workspace.id.in_(
                                    select(WorkspaceMember.workspace_id).where(
                                        WorkspaceMember.user_id == user_id
                                    )
                                )
                            )
                        )
                    )
                )
                task_list = list_result.scalar_one_or_none()
                if task_list:
                    list_name = task_list.name
                else:
                    logger.warning(f"Invalid list ID: {task_details['list_id']}")
                    return None
            
            # Return task suggestion (not saved to DB)
            return {
                "title": task_details.get("title", "Untitled Task"),
                "description": task_details.get("description"),
                "workspace_id": task_details.get("workspace_id"),
                "workspace_name": workspace_name,
                "list_id": task_details.get("list_id"),
                "list_name": list_name,
                "priority": task_details.get("priority", "medium"),
                "status": "todo",
                "due_date": task_details.get("due_date"),
                "suggested": True
            }
            
        except Exception as e:
            logger.error(f"Error creating task from AI: {str(e)}")
            return None

    async def _cleanup_old_messages(self, user_id: str, db: AsyncSession):
        """Clean up old messages to maintain the configured limit."""
        # Get the chat history limit from settings
        limit_setting = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "chat_history_limit")
        )
        limit_setting = limit_setting.scalar_one_or_none()
        limit = int(limit_setting.value) if limit_setting else 50
        
        # Count current messages
        result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.user_id == user_id)
        )
        message_count = result.scalar() or 0
        
        # If we're over the limit, delete oldest messages
        if message_count > limit:
            messages_to_delete = message_count - limit
            
            # Get IDs of oldest messages to delete
            result = await db.execute(
                select(ChatMessage.id)
                .where(ChatMessage.user_id == user_id)
                .order_by(ChatMessage.created_at.asc())
                .limit(messages_to_delete)
            )
            message_ids_to_delete = [row[0] for row in result]
            
            # Delete the messages
            if message_ids_to_delete:
                from sqlalchemy import delete
                await db.execute(
                    delete(ChatMessage).where(ChatMessage.id.in_(message_ids_to_delete))
                )
                await db.commit()
                logger.info(f"Cleaned up {messages_to_delete} old messages for user {user_id}")


# Global chat service instance
chat_service = ChatService()