"""
Base AI Provider interface
Created: 2025-07-02 22:00:00 PST
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Base exception for AI provider errors"""
    pass


class AIProviderUnavailableError(AIProviderError):
    """Raised when a provider is temporarily unavailable"""
    pass


class AIProviderConfigError(AIProviderError):
    """Raised when a provider is misconfigured"""
    pass


class AIResponse(BaseModel):
    """Standardized AI response format"""
    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, name: str):
        self.name = name
        self._initialized = False
        
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider with configuration.
        Returns True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def complete(
        self, 
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AIResponse:
        """
        Complete a prompt and return structured response.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            response_format: Optional format specification (e.g. {"type": "json_object"})
            **kwargs: Provider-specific parameters
            
        Returns:
            AIResponse object with completion
            
        Raises:
            AIProviderError: For general provider errors
            AIProviderUnavailableError: When provider is temporarily unavailable
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if provider is available and properly configured.
        
        Returns:
            True if provider is ready to use, False otherwise
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get provider name for logging and identification.
        
        Returns:
            Provider name string
        """
        return self.name
    
    @abstractmethod
    def get_priority(self) -> int:
        """
        Get provider priority (lower number = higher priority).
        
        Returns:
            Priority integer (1-100)
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the provider.
        
        Returns:
            Dictionary with health status information
        """
        try:
            available = await self.is_available()
            return {
                "provider": self.name,
                "available": available,
                "status": "healthy" if available else "unavailable"
            }
        except Exception as e:
            return {
                "provider": self.name,
                "available": False,
                "status": "error",
                "error": str(e)
            }
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """
        Helper to parse JSON responses safely.
        
        Args:
            content: JSON string to parse
            
        Returns:
            Parsed dictionary
            
        Raises:
            AIProviderError: If parsing fails
        """
        import json
        try:
            # Try to extract JSON if it's wrapped in markdown code blocks
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()
                    
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {content[:200]}...")
            raise AIProviderError(f"Invalid JSON response: {str(e)}")