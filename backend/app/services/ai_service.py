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

import redis.asyncio as redis
from pydantic import BaseModel

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


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service