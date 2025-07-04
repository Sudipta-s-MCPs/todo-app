"""
AI Service for semantic task analysis using Groq
Created: 2025-01-02 06:00:00 PST
"""

import os
import json
import hashlib
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache
from uuid import UUID

import redis.asyncio as redis
from pydantic import BaseModel, Field

from app.services.cache import get_redis_client
from app.utils.logging import get_logger
from app.services.dynamic_settings import dynamic_settings
from app.services.ai_providers import (
    AIProvider, AIProviderError, AIProviderUnavailableError,
    GroqProvider, HuggingFaceProvider, GeminiProvider
)

logger = get_logger(__name__)


class TaskAnalysis(BaseModel):
    """Result of AI task analysis"""
    is_duplicate: bool
    confidence: float
    reasoning: str
    suggested_action: str  # "create_new", "update_existing", "merge"
    suggested_title: Optional[str] = None
    suggested_workspace: Optional[str] = None  # workspace ID
    suggested_workspace_name: Optional[str] = None  # workspace name for display
    suggested_list: Optional[str] = None  # list ID
    suggested_list_name: Optional[str] = None  # list name for display
    suggested_priority: Optional[str] = None
    suggested_due_date: Optional[str] = None
    extracted_entities: Optional[Dict[str, Any]] = None
    provider_used: Optional[str] = None


class ConversationResponse(BaseModel):
    """Result of AI conversation processing"""
    intent: str  # greeting|task_creation|task_query|general_query|clarification|other
    use_pattern: bool = False
    pattern_command: Optional[str] = None
    response: str
    needs_clarification: bool = False
    task_details: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    provider_used: Optional[str] = None


class UsageTracker:
    """Track AI usage for cost control"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.daily_limit = dynamic_settings.AI_DAILY_TOKEN_LIMIT
        self.user_monthly_limit = dynamic_settings.AI_USER_MONTHLY_TOKEN_LIMIT
    
    async def check_and_update_usage(self, user_id: str, tokens: int) -> bool:
        """Check if usage is within limits and update counters"""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        
        # Check daily limit
        daily_key = f"ai_usage:daily:{today}"
        daily_usage = await self.redis.get(daily_key) or 0
        if int(daily_usage) + tokens > self.daily_limit:
            logger.warning(f"Daily AI token limit exceeded: {daily_usage} + {tokens} > {self.daily_limit}")
            return False
        
        # Check user monthly limit
        user_monthly_key = f"ai_usage:user:{user_id}:{month}"
        user_usage = await self.redis.get(user_monthly_key) or 0
        if int(user_usage) + tokens > self.user_monthly_limit:
            logger.warning(f"User {user_id} monthly token limit exceeded")
            return False
        
        # Update counters
        pipe = self.redis.pipeline()
        pipe.incrby(daily_key, tokens)
        pipe.expire(daily_key, 86400)  # 24 hours
        pipe.incrby(user_monthly_key, tokens)
        pipe.expire(user_monthly_key, 2592000)  # 30 days
        await pipe.execute()
        
        return True
    
    async def get_usage_stats(self, user_id: str) -> Dict[str, int]:
        """Get current usage statistics"""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        
        daily_usage = await self.redis.get(f"ai_usage:daily:{today}") or 0
        user_monthly_usage = await self.redis.get(f"ai_usage:user:{user_id}:{month}") or 0
        
        return {
            "daily_usage": int(daily_usage),
            "daily_limit": self.daily_limit,
            "user_monthly_usage": int(user_monthly_usage),
            "user_monthly_limit": self.user_monthly_limit
        }


class AIService:
    """Main AI service for task analysis with multi-provider support"""
    
    def __init__(self):
        self._providers: List[AIProvider] = []
        self._initialized = False
        self.cache_ttl = None
        self.temperature = None
        self.max_tokens = None
    
    async def _ensure_initialized(self):
        """Initialize AI providers based on configuration"""
        if self._initialized:
            return
        
        # Ensure dynamic settings are loaded
        try:
            if not dynamic_settings._loaded:
                logger.info("Refreshing dynamic settings for AI service initialization")
                await dynamic_settings.refresh()
        except Exception as e:
            logger.error(f"Failed to refresh dynamic settings: {e}")
        
        # Load settings
        self.cache_ttl = dynamic_settings.AI_CACHE_TTL
        self.temperature = dynamic_settings.AI_TEMPERATURE
        self.max_tokens = dynamic_settings.AI_MAX_TOKENS
        
        # Initialize providers based on configuration
        provider_mode = dynamic_settings.AI_PROVIDER_MODE
        
        if provider_mode == "groq_only":
            # Backward compatibility mode
            groq_provider = GroqProvider()
            if await groq_provider.initialize():
                self._providers = [groq_provider]
        else:
            # Hybrid mode - initialize all configured providers
            provider_priority = dynamic_settings.AI_PROVIDER_PRIORITY.split(",")
            available_providers = {
                "huggingface": HuggingFaceProvider,
                "gemini": GeminiProvider,
                "groq": GroqProvider
            }
            
            for provider_name in provider_priority:
                provider_name = provider_name.strip().lower()
                if provider_name in available_providers:
                    provider_class = available_providers[provider_name]
                    provider = provider_class()
                    if await provider.initialize():
                        self._providers.append(provider)
                        logger.info(f"Initialized {provider_name} provider")
                    else:
                        logger.warning(f"Failed to initialize {provider_name} provider")
            
            # Sort providers by priority
            self._providers.sort(key=lambda p: p.get_priority())
        
        self._initialized = True
        logger.info(f"AI Service initialized with {len(self._providers)} provider(s)")
    
    async def _call_provider(self, provider: AIProvider, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Call a specific provider and handle errors"""
        try:
            response = await provider.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            content = response.content
            return json.loads(content)
            
        except AIProviderUnavailableError as e:
            logger.warning(f"{provider.get_name()} temporarily unavailable: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"{provider.get_name()} failed: {str(e)}")
            return None
    
    def _get_cache_key(self, operation: str, content: str) -> str:
        """Generate cache key for AI responses"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"ai_cache:{operation}:{content_hash}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached AI response"""
        redis_client = await get_redis_client()
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info(f"AI cache hit for key: {cache_key}")
            return json.loads(cached)
        return None
    
    async def _cache_response(self, cache_key: str, response: Dict[str, Any]):
        """Cache AI response"""
        redis_client = await get_redis_client()
        await redis_client.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(response)
        )
    
    async def analyze_duplicate(
        self,
        new_task: str,
        existing_tasks: List[Dict[str, str]],
        user_id: str
    ) -> TaskAnalysis:
        """Analyze if a new task is a duplicate of existing tasks"""
        
        # Check cache first
        cache_content = f"{new_task}|{json.dumps(existing_tasks, sort_keys=True)}"
        cache_key = self._get_cache_key("duplicate", cache_content)
        cached = await self._get_cached_response(cache_key)
        if cached:
            return TaskAnalysis(**cached)
        
        # Prepare prompt
        existing_tasks_str = "\n".join([
            f"- {task['title']}: {task.get('description', 'No description')}"
            for task in existing_tasks[:10]  # Limit to 10 tasks to save tokens
        ])
        
        prompt = f"""Analyze if this new task is a duplicate or similar to existing tasks.

New task: {new_task}

Existing tasks:
{existing_tasks_str}

Respond in JSON format:
{{
    "is_duplicate": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "suggested_action": "create_new" or "update_existing" or "merge",
    "suggested_title": "improved title if needed"
}}"""
        
        # Check usage limits
        estimated_tokens = len(prompt.split()) * 2  # Rough estimate
        redis_client = await get_redis_client()
        usage_tracker = UsageTracker(redis_client)
        
        if not await usage_tracker.check_and_update_usage(user_id, estimated_tokens):
            # Fallback to non-AI response
            logger.warning(f"AI usage limit exceeded for user {user_id}")
            return TaskAnalysis(
                is_duplicate=False,
                confidence=0.0,
                reasoning="AI analysis unavailable due to usage limits",
                suggested_action="create_new"
            )
        
        # Ensure providers are initialized
        await self._ensure_initialized()
        
        if not self._providers:
            logger.warning("No AI providers available")
            return TaskAnalysis(
                is_duplicate=False,
                confidence=0.0,
                reasoning="AI service not configured. Please configure AI providers in admin settings.",
                suggested_action="create_new"
            )
        
        # Try each provider in priority order
        system_prompt = "You are a task management assistant. Analyze tasks for duplicates and provide suggestions in JSON format."
        
        for provider in self._providers:
            result = await self._call_provider(provider, prompt, system_prompt)
            if result:
                try:
                    analysis = TaskAnalysis(**result)
                    # Cache the response
                    await self._cache_response(cache_key, analysis.model_dump())
                    return analysis
                except Exception as e:
                    logger.error(f"Failed to parse response from {provider.get_name()}: {str(e)}")
                    continue
        
        # All providers failed - return fallback
        logger.error("All AI providers failed for duplicate analysis")
        return TaskAnalysis(
            is_duplicate=False,
            confidence=0.0,
            reasoning="AI analysis unavailable - all providers failed",
            suggested_action="create_new"
        )
    
    async def parse_natural_task(
        self,
        natural_text: str,
        workspaces: List[Dict[str, Any]],
        lists: List[Dict[str, Any]],
        user_id: str
    ) -> TaskAnalysis:
        """Parse natural language task input and extract structured data"""
        
        # Check cache
        cache_content = f"{natural_text}|{json.dumps(workspaces, sort_keys=True)}|{json.dumps(lists, sort_keys=True)}"
        cache_key = self._get_cache_key("parse", cache_content)
        cached = await self._get_cached_response(cache_key)
        if cached:
            return TaskAnalysis(**cached)
        
        # Prepare context - create a tree structure
        workspace_tree = []
        for ws in workspaces:
            ws_lists = [lst for lst in lists if lst.get('workspace_id') == ws['id']]
            workspace_tree.append({
                'name': ws['name'],
                'id': ws['id'],
                'lists': [{'name': lst['name'], 'id': lst['id']} for lst in ws_lists]
            })
        
        prompt = f"""Parse this natural language task and extract structured information.

Task: {natural_text}

Available workspaces and their lists:
{json.dumps(workspace_tree, indent=2)}

IMPORTANT RULES:
1. The suggested_title should be a SHORT, ACTIONABLE task title (3-8 words typically)
2. Remove workspace and list references from the title
3. Extract the core action as the title
4. Match workspace and list names case-insensitively
5. If a list is mentioned, also set the corresponding workspace
6. suggested_workspace should be the workspace ID (not name)
7. suggested_list should be the list ID (not name)

Examples:
- "in todo app workspace to fix profile page" → title: "Fix profile page", workspace: [TodoApp ID]
- "Add task to update docs in Dev workspace Backend list" → title: "Update docs", workspace: [Dev ID], list: [Backend ID]
- "Remember to buy groceries" → title: "Buy groceries"
- "Fix bug in frontend list" → title: "Fix bug", list: [frontend list ID], workspace: [workspace containing frontend list]

Extract and respond in JSON format:
{{
    "is_duplicate": false,
    "confidence": 1.0,
    "reasoning": "Task parsed successfully",
    "suggested_action": "create_new",
    "suggested_title": "SHORT extracted task title (core action only)",
    "suggested_workspace": "workspace ID from the tree or null",
    "suggested_workspace_name": "workspace name for display",
    "suggested_list": "list ID from the tree or null",
    "suggested_list_name": "list name for display",
    "suggested_priority": "low/medium/high or null",
    "suggested_due_date": "ISO date if mentioned or null",
    "extracted_entities": {{
        "people": ["names mentioned"],
        "projects": ["project names"],
        "locations": ["locations mentioned"]
    }}
}}"""
        
        # Check usage
        estimated_tokens = len(prompt.split()) * 2
        redis_client = await get_redis_client()
        usage_tracker = UsageTracker(redis_client)
        
        if not await usage_tracker.check_and_update_usage(user_id, estimated_tokens):
            # Basic parsing without AI
            return TaskAnalysis(
                is_duplicate=False,
                confidence=0.5,
                reasoning="AI parsing unavailable, using basic extraction",
                suggested_action="create_new",
                suggested_title=natural_text[:100],  # First 100 chars as title
                suggested_workspace=workspaces[0]['name'] if workspaces else None,
                suggested_list=lists[0]['name'] if lists else None,
                provider_used="none"
            )
        
        # Ensure providers are initialized
        await self._ensure_initialized()
        
        if not self._providers:
            logger.warning("No AI providers available")
            return TaskAnalysis(
                is_duplicate=False,
                confidence=0.5,
                reasoning="AI parsing unavailable, using basic extraction",
                suggested_action="create_new",
                suggested_title=natural_text[:100],  # First 100 chars as title
                suggested_workspace=workspaces[0]['name'] if workspaces else None,
                suggested_list=lists[0]['name'] if lists else None,
                provider_used="none"
            )
        
        # Try each provider in priority order
        system_prompt = "You are a task parsing assistant. Extract structured task information from natural language."
        
        for provider in self._providers:
            result = await self._call_provider(provider, prompt, system_prompt)
            if result:
                try:
                    analysis = TaskAnalysis(**result)
                    # Add provider information to the analysis
                    analysis.provider_used = provider.get_name()
                    # Cache the response
                    await self._cache_response(cache_key, analysis.model_dump())
                    return analysis
                except Exception as e:
                    logger.error(f"Failed to parse response from {provider.get_name()}: {str(e)}")
                    continue
        
        # All providers failed - return basic extraction
        logger.error("All AI providers failed for task parsing")
        return TaskAnalysis(
            is_duplicate=False,
            confidence=0.0,
            reasoning="AI parsing failed - all providers unavailable",
            suggested_action="create_new",
            suggested_title=natural_text[:100],
            provider_used="failed"
        )
    
    async def suggest_task_improvements(
        self,
        task_title: str,
        task_description: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Suggest improvements for task clarity and actionability"""
        
        # Check cache
        cache_content = f"{task_title}|{task_description}"
        cache_key = self._get_cache_key("improve", cache_content)
        cached = await self._get_cached_response(cache_key)
        if cached:
            return cached
        
        prompt = f"""Suggest improvements for this task:

Title: {task_title}
Description: {task_description or 'No description'}

Provide suggestions in JSON format:
{{
    "improved_title": "clearer, more actionable title",
    "improved_description": "detailed description with clear steps",
    "suggested_subtasks": ["subtask 1", "subtask 2"],
    "clarity_score": 0.0-1.0,
    "actionability_score": 0.0-1.0
}}"""
        
        # Check usage
        estimated_tokens = len(prompt.split()) * 2
        redis_client = await get_redis_client()
        usage_tracker = UsageTracker(redis_client)
        
        if not await usage_tracker.check_and_update_usage(user_id, estimated_tokens):
            # Return basic response
            return {
                "improved_title": task_title,
                "improved_description": task_description,
                "suggested_subtasks": [],
                "clarity_score": 0.5,
                "actionability_score": 0.5
            }
        
        # Ensure providers are initialized
        await self._ensure_initialized()
        
        if not self._providers:
            return {
                "improved_title": task_title,
                "improved_description": task_description,
                "suggested_subtasks": [],
                "clarity_score": 0.5,
                "actionability_score": 0.5
            }
        
        # Try each provider
        system_prompt = "You are a task improvement assistant. Analyze tasks and suggest improvements in JSON format."
        
        for provider in self._providers:
            result = await self._call_provider(provider, prompt, system_prompt)
            if result:
                # Cache and return
                await self._cache_response(cache_key, result)
                return result
        
        # Fallback if all providers fail
        return {
            "improved_title": task_title,
            "improved_description": task_description,
            "suggested_subtasks": [],
            "clarity_score": 0.5,
            "actionability_score": 0.5
        }
    
    async def analyze_task_intent(
        self,
        text: str,
        workspaces: List[Dict[str, Any]],
        lists: List[Dict[str, Any]],
        existing_tasks: Optional[List[Dict[str, Any]]] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Analyze text to determine task-related intent and extract details
        
        Returns dict with:
        - is_task_related: bool
        - action: "create" | "update" | "query" | "complete"
        - task_details: extracted task information
        - suggestions: list of suggestions
        """
        # Use parse_natural_task for task extraction
        analysis = await self.parse_natural_task(text, workspaces, lists, user_id or "system")
        
        # Check for duplicate if existing tasks provided
        is_duplicate = False
        duplicate_suggestions = []
        
        if existing_tasks and analysis.suggested_title:
            dup_analysis = await self.analyze_duplicate(
                analysis.suggested_title,
                existing_tasks[:10],  # Check against recent tasks
                user_id or "system"
            )
            is_duplicate = dup_analysis.is_duplicate
            if is_duplicate:
                duplicate_suggestions.append({
                    "action": dup_analysis.suggested_action,
                    "reasoning": dup_analysis.reasoning
                })
        
        return {
            "is_task_related": bool(analysis.suggested_title),
            "action": "create" if analysis.suggested_title else "unknown",
            "task_details": {
                "title": analysis.suggested_title,
                "description": None,
                "workspace_id": analysis.suggested_workspace,
                "list_id": analysis.suggested_list,
                "priority": analysis.suggested_priority or "medium",
                "due_date": analysis.suggested_due_date
            } if analysis.suggested_title else None,
            "is_duplicate": is_duplicate,
            "suggestions": duplicate_suggestions,
            "confidence": analysis.confidence,
            "provider_used": analysis.provider_used
        }
    
    async def process_conversation(
        self,
        message: str,
        user_context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        mode: str = "chat",
        user_id: str = None
    ) -> ConversationResponse:
        """
        Unified conversation processing for all interfaces
        
        Args:
            message: User's input message
            user_context: Contains workspaces, lists, task counts, etc.
            conversation_history: Previous messages for context
            mode: "chat" | "mcp" | "api" - Interface type for tailored responses
            user_id: User ID for usage tracking
        
        Returns:
            ConversationResponse with intent, response, and optional task details
        """
        # Check cache
        cache_content = f"{mode}:{message}:{json.dumps(user_context, sort_keys=True)}"
        cache_key = self._get_cache_key("conversation", cache_content)
        cached = await self._get_cached_response(cache_key)
        if cached:
            return ConversationResponse(**cached)
        
        # Format conversation history
        conversation_history_str = ""
        if conversation_history:
            conversation_history_str = "Recent conversation:\n"
            for msg in conversation_history[-6:]:  # Only use last 6 messages
                role = "User" if msg.get("role") == "user" else "Assistant"
                conversation_history_str += f"{role}: {msg.get('content', '')}\n"
        else:
            conversation_history_str = "This is the start of the conversation."
        
        # Create comprehensive prompt
        system_prompt = f"""You are a friendly and helpful AI assistant for Smart ToDo, a task management app. You help users manage their tasks, workspaces, and lists while maintaining a natural, conversational tone.

IMPORTANT GUIDELINES:
1. Be conversational and friendly - respond like a helpful personal assistant, not a robot
2. Handle greetings warmly (hi, hello, hey, good morning, etc.)
3. When users say things like "I need to..." or "I have to...", understand they want to create a task
4. For TASK CREATION: Always use task_details, NOT pattern commands. Extract all context like workspace, list, priority from the request
5. Only use pattern commands for simple operations like listing tasks or marking tasks complete
6. Ask for clarification when requests are unclear
7. Keep responses concise but friendly
8. Interface mode: {mode} - adjust formality accordingly

Pattern commands are ONLY for these simple operations:
- Task listing: "show tasks", "list tasks", "show [priority] priority tasks"
- Task completion: "complete task [name]", "mark [task] as done"
- Workspace operations: "show workspaces"

For task creation, ALWAYS set:
- intent: "task_creation"
- use_pattern: false
- task_details with extracted information

CRITICAL: When setting pattern_command, replace placeholders with ACTUAL values from the user's request.

CONVERSATION CONTEXT:
{conversation_history_str}

USER CONTEXT:
{json.dumps(user_context, indent=2)}

Analyze the user's request and respond with:
{{
    "intent": "greeting|task_creation|task_query|general_query|clarification|other",
    "use_pattern": true/false,
    "pattern_command": "exact command if use_pattern is true",
    "response": "friendly, natural response to user",
    "needs_clarification": true/false,
    "task_details": {{ // only if creating a task
        "title": "task title",
        "description": "optional description",
        "workspace_id": "workspace UUID",
        "list_id": "list UUID",
        "priority": "low|medium|high",
        "due_date": "ISO date or null"
    }},
    "confidence": 0.0-1.0
}}"""
        
        prompt = f"User request: {message}"
        
        # Check usage
        estimated_tokens = len(prompt.split()) * 2 + len(system_prompt.split())
        redis_client = await get_redis_client()
        usage_tracker = UsageTracker(redis_client)
        
        if user_id and not await usage_tracker.check_and_update_usage(user_id, estimated_tokens):
            # Return basic response without AI
            return ConversationResponse(
                intent="other",
                use_pattern=False,
                response="I'm currently unable to process your request due to usage limits. Please try again later.",
                confidence=0.0,
                provider_used="none"
            )
        
        # Ensure providers are initialized
        await self._ensure_initialized()
        
        if not self._providers:
            return ConversationResponse(
                intent="other",
                use_pattern=False,
                response="I'm not properly configured yet. Please contact your administrator.",
                confidence=0.0,
                provider_used="none"
            )
        
        # Try each provider in priority order
        for provider in self._providers:
            result = await self._call_provider(provider, prompt, system_prompt)
            if result:
                try:
                    response = ConversationResponse(**result)
                    response.provider_used = provider.get_name()
                    # Cache the response
                    await self._cache_response(cache_key, response.model_dump())
                    return response
                except Exception as e:
                    logger.error(f"Failed to parse response from {provider.get_name()}: {str(e)}")
                    continue
        
        # All providers failed - return fallback
        return ConversationResponse(
            intent="other",
            use_pattern=False,
            response="I'm having trouble understanding your request. Could you please rephrase it?",
            confidence=0.0,
            provider_used="failed"
        )
    
    async def get_smart_task_recommendations(
        self,
        user_id: str,
        all_tasks: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get smart task recommendations using Qdrant and AI
        
        Returns list of tasks with recommendation metadata
        """
        from app.services.vector_service import get_vector_service
        from datetime import datetime, timedelta
        
        # Check usage limits
        if not await self.usage_tracker.check_and_update_usage(user_id, 1000):
            logger.warning(f"Usage limit exceeded for user {user_id}")
            # Return simple rule-based recommendations
            return self._get_rule_based_recommendations(all_tasks, limit)
        
        recommendations = []
        current_time = datetime.utcnow()
        
        # Phase 1: Use Qdrant to find contextually relevant tasks
        vector_service = get_vector_service()
        qdrant_tasks = []
        
        if vector_service and vector_service.client:
            urgency_queries = [
                "urgent overdue tasks that need immediate attention",
                "tasks due today or tomorrow", 
                "high priority important tasks",
                "tasks with upcoming reminders in the next 24 hours"
            ]
            
            task_ids_from_qdrant = set()
            for query in urgency_queries:
                try:
                    similar_tasks = await vector_service.search_similar_tasks(
                        query_text=query,
                        user_id=UUID(user_id) if user_id else None,
                        limit=20,
                        score_threshold=0.5
                    )
                    for task_data, score in similar_tasks:
                        task_id = task_data.get('id')
                        if task_id and task_id not in task_ids_from_qdrant:
                            task_ids_from_qdrant.add(task_id)
                            qdrant_tasks.append((task_data, score))
                except Exception as e:
                    logger.error(f"Qdrant search failed: {str(e)}")
        
        # Phase 2: Traditional filtering for comprehensive coverage
        urgent_tasks = []
        for task in all_tasks:
            if task.get('status') in ['completed', 'archived']:
                continue
                
            urgency_score = 0.0
            category = "normal"
            
            # Check if task is overdue
            if task.get('due_date'):
                due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                if due_date < current_time:
                    urgency_score = 1.0
                    category = "overdue"
                elif due_date.date() == current_time.date():
                    urgency_score = 0.9
                    category = "due_today"
                elif due_date < current_time + timedelta(days=2):
                    urgency_score = 0.8
                    category = "due_tomorrow"
                elif due_date < current_time + timedelta(days=7):
                    urgency_score = 0.6
                    category = "due_this_week"
            
            # Check priority
            if task.get('priority') == 'high' and urgency_score < 0.7:
                urgency_score = max(urgency_score, 0.7)
                if category == "normal":
                    category = "high_priority"
            
            # Check for reminders
            if task.get('reminder_date'):
                reminder_date = datetime.fromisoformat(task['reminder_date'].replace('Z', '+00:00'))
                if reminder_date < current_time + timedelta(hours=24):
                    urgency_score = max(urgency_score, 0.8)
                    if category == "normal":
                        category = "reminder_soon"
            
            # Check for stale tasks
            if task.get('created_at'):
                created_date = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
                days_old = (current_time - created_date).days
                if days_old > 30 and urgency_score < 0.5:
                    urgency_score = max(urgency_score, 0.5)
                    if category == "normal":
                        category = "stale"
            
            if urgency_score > 0.3:
                task['urgency_score'] = urgency_score
                task['category'] = category
                urgent_tasks.append(task)
        
        # Phase 3: Combine and deduplicate
        combined_tasks = []
        seen_ids = set()
        
        # Add Qdrant results first (they have semantic relevance)
        for task_data, vector_score in qdrant_tasks:
            task_id = task_data.get('id')
            if task_id not in seen_ids:
                seen_ids.add(task_id)
                # Find full task data
                full_task = next((t for t in all_tasks if t.get('id') == task_id), None)
                if full_task:
                    full_task['vector_relevance_score'] = vector_score
                    combined_tasks.append(full_task)
        
        # Add urgent tasks from traditional filtering
        for task in urgent_tasks:
            if task.get('id') not in seen_ids:
                seen_ids.add(task['id'])
                combined_tasks.append(task)
        
        # Phase 4: Use AI for final ranking (if we have tasks to rank)
        if combined_tasks:
            # Limit tasks sent to AI to reduce token usage
            tasks_for_ai = combined_tasks[:30]
            
            prompt = f"""Analyze these tasks and recommend the top {limit} that need immediate attention.
Consider: overdue status, due dates, priority levels, reminders, task age, and semantic relevance.

Tasks:
{json.dumps([{
    'id': t.get('id'),
    'title': t.get('title'),
    'priority': t.get('priority'),
    'due_date': t.get('due_date'),
    'reminder_date': t.get('reminder_date'),
    'created_at': t.get('created_at'),
    'urgency_score': t.get('urgency_score', 0),
    'category': t.get('category', 'normal'),
    'vector_score': t.get('vector_relevance_score', 0)
} for t in tasks_for_ai], indent=2)}

Return a JSON array of the top {limit} task IDs with reasoning:
[{{"id": "task_id", "reason": "brief explanation", "final_score": 0.0-1.0}}]"""

            try:
                # Try to get AI recommendations
                for provider in self._providers:
                    result = await self._call_provider(
                        provider, 
                        prompt,
                        "You are a task prioritization expert. Analyze tasks and recommend the most urgent ones."
                    )
                    if result:
                        try:
                            ai_recommendations = json.loads(result)
                            
                            # Build final recommendations
                            for rec in ai_recommendations[:limit]:
                                task_id = rec.get('id')
                                task = next((t for t in combined_tasks if t.get('id') == task_id), None)
                                if task:
                                    recommendations.append({
                                        'task': task,
                                        'recommendation_reason': rec.get('reason', 'High priority task'),
                                        'urgency_score': rec.get('final_score', task.get('urgency_score', 0.5)),
                                        'category': task.get('category', 'normal'),
                                        'vector_relevance_score': task.get('vector_relevance_score')
                                    })
                            
                            if recommendations:
                                return recommendations
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse AI response from {provider.get_name()}")
                            continue
            except Exception as e:
                logger.error(f"AI ranking failed: {str(e)}")
        
        # Fallback: Return top tasks by urgency score
        combined_tasks.sort(key=lambda x: x.get('urgency_score', 0), reverse=True)
        for task in combined_tasks[:limit]:
            recommendations.append({
                'task': task,
                'recommendation_reason': self._get_recommendation_reason(task),
                'urgency_score': task.get('urgency_score', 0.5),
                'category': task.get('category', 'normal'),
                'vector_relevance_score': task.get('vector_relevance_score')
            })
        
        return recommendations
    
    def _get_rule_based_recommendations(self, all_tasks: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Simple rule-based recommendations when AI is unavailable"""
        from datetime import datetime, timedelta
        
        current_time = datetime.utcnow()
        recommendations = []
        
        # Score and categorize tasks
        for task in all_tasks:
            if task.get('status') in ['completed', 'archived']:
                continue
            
            urgency_score = 0.0
            category = "normal"
            reason = ""
            
            # Check overdue
            if task.get('due_date'):
                due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                if due_date < current_time:
                    urgency_score = 1.0
                    category = "overdue"
                    days_overdue = (current_time - due_date).days
                    reason = f"Overdue by {days_overdue} day(s)"
                elif due_date.date() == current_time.date():
                    urgency_score = 0.9
                    category = "due_today"
                    reason = "Due today"
                elif due_date < current_time + timedelta(days=1):
                    urgency_score = 0.8
                    category = "due_tomorrow"
                    reason = "Due tomorrow"
            
            # Check priority
            if task.get('priority') == 'high':
                urgency_score = max(urgency_score, 0.7)
                if not reason:
                    reason = "High priority task"
                    category = "high_priority"
            
            if urgency_score > 0:
                recommendations.append({
                    'task': task,
                    'recommendation_reason': reason,
                    'urgency_score': urgency_score,
                    'category': category,
                    'vector_relevance_score': None
                })
        
        # Sort by urgency and return top N
        recommendations.sort(key=lambda x: x['urgency_score'], reverse=True)
        return recommendations[:limit]
    
    def _get_recommendation_reason(self, task: Dict[str, Any]) -> str:
        """Generate a reason for why this task is recommended"""
        category = task.get('category', 'normal')
        
        reasons = {
            'overdue': 'This task is overdue and needs immediate attention',
            'due_today': 'This task is due today',
            'due_tomorrow': 'This task is due tomorrow',
            'due_this_week': 'This task is due this week',
            'high_priority': 'This is a high priority task',
            'reminder_soon': 'You have a reminder set for this task',
            'stale': 'This task has been pending for a while',
            'related_cluster': 'This task is part of an important project'
        }
        
        return reasons.get(category, 'This task needs your attention')


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service