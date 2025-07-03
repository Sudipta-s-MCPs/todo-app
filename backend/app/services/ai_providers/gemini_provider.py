"""
Google Gemini AI Provider implementation
Created: 2025-07-02 22:15:00 PST
"""

from typing import Dict, Any, Optional
import logging
import httpx
import json

from app.services.dynamic_settings import dynamic_settings
from .base import AIProvider, AIResponse, AIProviderError, AIProviderUnavailableError

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini AI provider implementation"""
    
    def __init__(self):
        super().__init__("gemini")
        self.api_key = None
        self.model = None
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
    async def initialize(self) -> bool:
        """Initialize Gemini provider with API key from settings"""
        try:
            self.api_key = dynamic_settings.GEMINI_API_KEY
            if not self.api_key:
                logger.warning("Gemini API key not configured")
                return False
                
            self.model = dynamic_settings.GEMINI_MODEL
            self._initialized = True
            logger.info(f"Gemini provider initialized with model: {self.model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini provider: {str(e)}")
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
        """Complete a prompt using Google Gemini API"""
        if not self._initialized or not self.api_key:
            raise AIProviderError("Gemini provider not initialized")
            
        try:
            # Prepare the content
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt
                
            # Handle JSON response format request
            if response_format and response_format.get("type") == "json_object":
                full_prompt += "\n\nPlease respond in valid JSON format only."
            
            # Prepare request payload for Gemini
            payload = {
                "contents": [{
                    "parts": [{
                        "text": full_prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "topK": 1,
                    "topP": 1
                }
            }
            
            # Make API request
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 429:
                    raise AIProviderUnavailableError("Gemini rate limit exceeded")
                    
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                
                # Extract text from Gemini response format
                try:
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError) as e:
                    logger.error(f"Unexpected Gemini response format: {result}")
                    raise AIProviderError(f"Failed to parse Gemini response: {str(e)}")
                
                # Clean up response
                content = content.strip()
                
                # For JSON responses, validate and clean
                if response_format and response_format.get("type") == "json_object":
                    try:
                        parsed = self._parse_json_response(content)
                        content = json.dumps(parsed)
                    except:
                        pass
                
                # Extract usage if available
                usage = None
                if "usageMetadata" in result:
                    metadata = result["usageMetadata"]
                    usage = {
                        "prompt_tokens": metadata.get("promptTokenCount", 0),
                        "completion_tokens": metadata.get("candidatesTokenCount", 0),
                        "total_tokens": metadata.get("totalTokenCount", 0)
                    }
                
                return AIResponse(
                    content=content,
                    usage=usage,
                    model=self.model,
                    provider=self.name
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API request failed: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 403:
                raise AIProviderError("Gemini API key is invalid or doesn't have access")
            elif e.response.status_code == 429:
                raise AIProviderUnavailableError("Gemini rate limit exceeded")
            raise AIProviderError(f"Gemini API error: {str(e)}")
        except Exception as e:
            logger.error(f"Gemini completion failed: {str(e)}")
            raise AIProviderError(f"Gemini completion failed: {str(e)}")
    
    async def is_available(self) -> bool:
        """Check if Gemini provider is available"""
        if not self._initialized:
            await self.initialize()
            
        return self._initialized and self.api_key is not None
    
    def get_priority(self) -> int:
        """Get provider priority - Gemini is medium priority (free tier + cheap)"""
        return 20  # Medium priority
    
    def get_name(self) -> str:
        """Get provider name"""
        return self.name