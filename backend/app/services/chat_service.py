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
from app.models.chat import ChatMessage
from app.models.settings import SystemSetting
from app.schemas.task import TaskCreate
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat interactions with hybrid approach."""
    
    PATTERN_COMMANDS = {
        # Task creation patterns
        r"^(create|add|new)\s+(a\s+)?task\s+(.+)$": "create_task",
        r"^remind\s+me\s+to\s+(.+)$": "create_task",
        r"^todo:\s*(.+)$": "create_task",
        
        # Task listing patterns
        r"^(show|list|get)\s+(my\s+)?(all\s+)?tasks?$": "list_tasks",
        r"^what\s+(tasks?\s+)?do\s+i\s+have\??$": "list_tasks",
        r"^(show|list)\s+tasks?\s+in\s+(.+)$": "list_workspace_tasks",
        
        # Priority-based task listing
        r"^(show|list|get)\s+(my\s+)?(high|medium|low)\s+priority\s+tasks?$": "list_priority_tasks",
        
        # Date-based task listing
        r"^(what|which|show|list)\s+tasks?\s+(are\s+)?due\s+(today|tomorrow|this\s+week|next\s+week)\??$": "list_due_tasks",
        r"^(what|which|show|list)\s+(is|are)\s+due\s+(today|tomorrow|this\s+week|next\s+week)\??$": "list_due_tasks",
        
        # Task status updates
        r"^(complete|finish|done)\s+(with\s+)?task\s+(.+)$": "complete_task",
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
        
    def _serialize_task(self, task: Task) -> Dict[str, Any]:
        """Serialize a task object to dictionary."""
        if isinstance(task, dict):
            # Already serialized
            return task
        
        return {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat(),
            "list_id": str(task.list_id)
        }
        
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
        
        # Save user message to database
        user_message = ChatMessage(
            user_id=user_id,
            content=content,
            sender="user",
            message_metadata=None
        )
        db.add(user_message)
        await db.commit()
        
        # Check for pattern match first
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
                    "action": command_result.get("action")
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
                "usedAI": False
            }
        
        # Use AI for natural language task creation
        looks_like_task = await self._looks_like_task_creation(content)
        logger.info(f"Task detection for '{content}': {looks_like_task}")
        
        if looks_like_task:
            logger.info(f"Processing with AI: '{content}'")
            ai_result = await self._process_with_ai(content, user_id, db)
            
            # Save assistant response
            assistant_message = ChatMessage(
                user_id=user_id,
                content=ai_result["response"],
                sender="assistant",
                message_metadata={
                    "type": ai_result.get("type", "task"),
                    "usedAI": True,
                    "confidence": ai_result.get("confidence"),
                    "action": "create_task"
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
                "action": "create_task",
                "usedAI": True
            }
        
        # Default response for unrecognized input
        default_content = "I'm not sure what you want me to do. Try saying something like 'create task buy groceries' or 'show my tasks'. Type 'help' for more examples."
        assistant_message = ChatMessage(
            user_id=user_id,
            content=default_content,
            sender="assistant",
            message_metadata={
                "type": "error",
                "usedAI": False
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
            "urgent", "important", "asap", "priority",
            "meeting", "appointment", "call", "conference", "session",
            "remind", "schedule", "plan", "organize", "arrange",
            "at", "pm", "am", "o'clock", "time", "due"
        ]
        
        content_lower = content.lower()
        logger.debug(f"Task detection debug - content_lower: '{content_lower}'")
        
        # Check for task-like keywords
        found_keywords = [kw for kw in task_keywords if kw in content_lower]
        logger.debug(f"Task detection debug - found keywords: {found_keywords}")
        
        if found_keywords:
            logger.debug("Task detection: MATCHED by keywords")
            return True
        
        # Check for imperative mood (starts with verb)
        first_word = content_lower.split()[0] if content.split() else ""
        imperative_verbs = [
            "buy", "get", "call", "email", "send", "write", "read",
            "finish", "complete", "review", "prepare", "schedule",
            "book", "pay", "fix", "clean", "organize", "update",
            "create", "add", "make", "do", "start", "begin",
            "plan", "arrange", "set", "meet", "attend", "join",
            "contact", "reach", "discuss", "talk", "interview"
        ]
        
        logger.debug(f"Task detection debug - first_word: '{first_word}', in imperative_verbs: {first_word in imperative_verbs}")
        
        if first_word in imperative_verbs:
            logger.debug("Task detection: MATCHED by imperative verb")
            return True
        
        logger.debug("Task detection: NO MATCH")
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
            
            # Get lists for context
            lists = []
            for workspace in workspaces:
                workspace_lists = await db.execute(
                    select(List).where(List.workspace_id == workspace.id)
                )
                for lst in workspace_lists.scalars():
                    lists.append({
                        "id": lst.id,
                        "name": lst.name,
                        "workspace_name": workspace.name
                    })
            
            # Parse task with AI
            analysis = await get_ai_service().parse_natural_task(
                content, 
                [{"id": w.id, "name": w.name} for w in workspaces],
                lists,
                user_id
            )
            
            if not analysis.suggested_title:
                return {
                    "response": "I couldn't understand that as a task. Could you rephrase it?",
                    "type": "error"
                }
            
            # Find the workspace by name or use default
            workspace_id = None
            if analysis.suggested_workspace:
                workspace = next((w for w in workspaces if w.name.lower() == analysis.suggested_workspace.lower()), None)
                if workspace:
                    workspace_id = workspace.id
            
            if not workspace_id and workspaces:
                # Use personal workspace or first available
                personal_workspace = next((w for w in workspaces if w.type == "personal"), None)
                workspace_id = personal_workspace.id if personal_workspace else workspaces[0].id
            
            if not workspace_id:
                return {
                    "response": "No workspace found. Please create a workspace first.",
                    "type": "error"
                }
            
            # Parse due date if provided
            due_date = None
            if analysis.suggested_due_date:
                try:
                    due_date = datetime.fromisoformat(analysis.suggested_due_date).date()
                except:
                    pass
            
            # Create the task
            task_data = TaskCreate(
                title=analysis.suggested_title,
                description=analysis.extracted_entities.get("description") if analysis.extracted_entities else None,
                workspace_id=workspace_id,
                priority=analysis.suggested_priority or "medium",
                due_date=due_date,
                tags=analysis.extracted_entities.get("projects", []) if analysis.extracted_entities else []
            )
            
            # Get default list for workspace
            default_list = await db.execute(
                select(List).where(
                    and_(
                        List.workspace_id == workspace_id,
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
                title=analysis.suggested_title,
                description=analysis.extracted_entities.get("description") if analysis.extracted_entities else None,
                list_id=default_list.id,
                priority=analysis.suggested_priority or "medium",
                status="todo",
                due_date=due_date,
                position=0,
                created_by=user_id,
                created_via_method="chat_ai",
                task_metadata={"tags": analysis.extracted_entities.get("projects", []) if analysis.extracted_entities else []}
            )
            
            db.add(new_task)
            await db.commit()
            await db.refresh(new_task)
            
            task = new_task
            
            # Get workspace name from the list's workspace
            workspace_result = await db.execute(
                select(Workspace).join(List).where(List.id == new_task.list_id)
            )
            workspace = workspace_result.scalar_one_or_none()
            workspace_name = workspace.name if workspace else "Personal"
            
            response = f"✅ Created task: \"{task.title}\" in {workspace_name}"
            if task.due_date:
                response += f" (due {task.due_date.strftime('%b %d')})"
            
            return {
                "response": response,
                "type": "task",
                "tasks": [self._serialize_task(task)],
                "confidence": analysis.confidence if analysis else 0.9
            }
            
        except Exception as e:
            logger.error(f"AI processing error: {str(e)}")
            
            # Check if it's a configuration error (missing API key)
            if "api_key" in str(e).lower() or "groq_api_key" in str(e).lower():
                # Try fallback task creation
                fallback_result = await self._fallback_task_creation(content, user_id, db)
                if fallback_result:
                    return fallback_result
                    
                return {
                    "response": "AI processing is currently unavailable. Please use simple commands like 'create task [title]' or contact your administrator to configure the AI service.",
                    "type": "error"
                }
            
            # For other AI errors, try fallback
            fallback_result = await self._fallback_task_creation(content, user_id, db)
            if fallback_result:
                return fallback_result
                
            return {
                "response": "I had trouble understanding that. Please try rephrasing or use a simple command like 'create task [title]'.",
                "type": "error"
            }
    
    async def _fallback_task_creation(
        self, 
        content: str, 
        user_id: str, 
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Fallback task creation when AI is not available."""
        try:
            # Get user's workspaces
            workspaces = await db.execute(
                select(Workspace).where(Workspace.owner_id == user_id)
            )
            workspaces = workspaces.scalars().all()
            
            if not workspaces:
                return {
                    "response": "No workspace found. Please create a workspace first, then try: 'create task [your task title]'",
                    "type": "error"
                }
            
            # Simple task title extraction
            task_title = self._extract_task_title_simple(content)
            if not task_title:
                return None
                
            # Use first workspace
            workspace = workspaces[0]
            
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
            
            # Create task
            task = Task(
                title=task_title,
                list_id=default_list.id,
                priority="medium",
                status="todo",
                position=0,
                created_by=user_id,
                created_via_method="chat_fallback"
            )
            
            db.add(task)
            await db.commit()
            await db.refresh(task)
            
            return {
                "response": f"✅ Created task: \"{task.title}\" (AI processing unavailable, used basic parsing)",
                "type": "task",
                "tasks": [self._serialize_task(task)]
            }
            
        except Exception as e:
            logger.error(f"Fallback task creation error: {str(e)}")
            return None
    
    def _extract_task_title_simple(self, content: str) -> Optional[str]:
        """Simple task title extraction for fallback."""
        content = content.strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            "schedule ", "plan ", "remind me to ", "i need to ", "todo: ",
            "task: ", "create task ", "add task ", "new task "
        ]
        
        content_lower = content.lower()
        for prefix in prefixes_to_remove:
            if content_lower.startswith(prefix):
                content = content[len(prefix):].strip()
                break
        
        # Clean up the title
        if content and len(content) > 2:
            return content[:100]  # Limit length
            
        return None
    
    async def _handle_create_task(
        self, 
        match: re.Match, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle pattern-based task creation."""
        # Extract task title from the match
        # Handle the optional 'a' in "create a task"
        if match.lastindex == 3:
            task_title = match.group(3)
        elif match.lastindex == 2:
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
            "tasks": [self._serialize_task(task)]
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
            select(Task).where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"]),
                    Task.priority == priority
                )
            ).order_by(Task.created_at.desc()).limit(10)
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
            response += f"{i}. {status_emoji} {priority_emoji} {task.title}"
            if task.due_date:
                response += f" (due {task.due_date.strftime('%b %d')})"
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
            select(Task).where(
                and_(
                    Task.created_by == user_id,
                    Task.status.in_(["todo", "in_progress"]),
                    Task.due_date.isnot(None),
                    Task.due_date >= start_date,
                    Task.due_date <= end_date
                )
            ).order_by(Task.due_date.asc())
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
            response += f"{i}. {status_emoji} {priority_emoji} {task.title}"
            response += f" (due {task.due_date.strftime('%b %d')})"
            response += "\n"
        
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
• "Remind me to call John tomorrow"
• "Todo: finish the report"
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
    ) -> "List[Dict[str, Any]]":
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