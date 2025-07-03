"""
Groq AI Provider implementation
Created: 2025-07-02 22:05:00 PST
"""

from typing import Dict, Any, Optional
import logging
from groq import Groq
from groq.types.chat import ChatCompletion

from app.services.dynamic_settings import dynamic_settings
from .base import AIProvider, AIResponse, AIProviderError, AIProviderUnavailableError

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Groq AI provider implementation"""
    
    def __init__(self):
        super().__init__("groq")
        self._client = None
        self.model = None
        
    async def initialize(self) -> bool:
        """Initialize Groq client with API key from settings"""
        try:
            api_key = dynamic_settings.GROQ_API_KEY
            if not api_key:
                logger.warning("Groq API key not configured")
                return False
                
            # Initialize Groq client without proxies parameter
            try:
                self._client = Groq(api_key=api_key)
            except TypeError as te:
                # Handle case where Groq doesn't accept certain parameters
                logger.warning(f"Groq initialization parameter issue: {str(te)}")
                # Try alternative initialization if needed
                import groq
                self._client = groq.Groq(api_key=api_key)
                
            self.model = dynamic_settings.GROQ_MODEL
            self._initialized = True
            logger.info(f"Groq provider initialized with model: {self.model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Groq provider: {str(e)}")
            return False
    
    async def complete(
        self, 
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AIResponse:
        """Complete a prompt using Groq"""
        if not self._initialized or not self._client:
            raise AIProviderError("Groq provider not initialized")
            
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare API call parameters
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Add response format if specified
            if response_format:
                params["response_format"] = response_format
                
            # Make API call
            response: ChatCompletion = self._client.chat.completions.create(**params)
            
            # Extract response
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else None
            
            return AIResponse(
                content=content,
                usage=usage,
                model=self.model,
                provider=self.name
            )
            
        except Exception as e:
            logger.error(f"Groq completion failed: {str(e)}")
            if "rate_limit" in str(e).lower():
                raise AIProviderUnavailableError(f"Groq rate limit exceeded: {str(e)}")
            raise AIProviderError(f"Groq completion failed: {str(e)}")
    
    async def is_available(self) -> bool:
        """Check if Groq provider is available"""
        if not self._initialized:
            # Try to initialize if not already done
            await self.initialize()
            
        return self._initialized and self._client is not None
    
    def get_priority(self) -> int:
        """Get provider priority - Groq is lowest priority (highest cost)"""
        return 30  # Lower priority = higher number
    
    def get_name(self) -> str:
        """Get provider name"""
        return self.name