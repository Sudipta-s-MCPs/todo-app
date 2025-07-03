"""
HuggingFace AI Provider implementation
Updated: 2025-07-02 22:30:00 PST - Migrated to new Inference Providers API
Fixed: 2025-07-02 23:45:00 PST - Direct router.huggingface.co integration
Final: 2025-07-02 24:00:00 PST - Proper InferenceClient implementation with provider support
Updated: 2025-07-03 - Added timeout handling for better reliability
Updated: 2025-07-03 07:45:00 PST - Added hf-inference provider support with api_key parameter
"""

from typing import Dict, Any, Optional, List
import logging
import json
import asyncio

from app.services.dynamic_settings import dynamic_settings
from .base import AIProvider, AIResponse, AIProviderError, AIProviderUnavailableError

logger = logging.getLogger(__name__)


class HuggingFaceProvider(AIProvider):
    """HuggingFace Inference Providers API implementation"""
    
    def __init__(self):
        super().__init__("huggingface")
        self.api_token = None
        self.model = None
        self.provider = None
        self.client = None
        
    async def initialize(self) -> bool:
        """Initialize HuggingFace provider with API token from settings"""
        try:
            # Ensure dynamic settings are loaded
            if not dynamic_settings._loaded:
                logger.info("Loading dynamic settings for HuggingFace provider")
                await dynamic_settings.refresh()
            
            self.api_token = dynamic_settings.HUGGINGFACE_API_TOKEN
            if not self.api_token:
                logger.warning("HuggingFace API token not configured")
                return False
                
            self.model = dynamic_settings.HUGGINGFACE_MODEL
            # Get provider preference, default to "auto" for automatic selection
            self.provider = getattr(dynamic_settings, 'HUGGINGFACE_PROVIDER', 'auto')
            
            # Initialize InferenceClient with proper provider support
            try:
                from huggingface_hub import InferenceClient
                
                # Create InferenceClient with provider and token/api_key
                if self.provider in ["novita", "hf-inference"]:
                    # Novita and hf-inference providers use api_key parameter
                    self.client = InferenceClient(provider=self.provider, api_key=self.api_token)
                elif self.provider == "auto":
                    # Let HuggingFace automatically select the best provider
                    self.client = InferenceClient(provider="auto", token=self.api_token)
                else:
                    # Use specific provider with token
                    self.client = InferenceClient(
                        provider=self.provider,
                        token=self.api_token
                    )
                
                # Test the client with a simple call to validate setup
                try:
                    # For model validation, we need to attempt a quick inference
                    # If the model isn't available, this will help us detect it early
                    if self.model:
                        # Try a minimal request to test the model
                        test_messages = [{"role": "user", "content": "Hi"}]
                        if self.provider in ["novita", "hf-inference"]:
                            test_response = self.client.chat.completions.create(
                                messages=test_messages,
                                model=self.model,
                                max_tokens=1
                            )
                        else:
                            test_response = self.client.chat_completion(
                                messages=test_messages,
                                model=self.model,
                                max_tokens=1
                            )
                        logger.info(f"HuggingFace model '{self.model}' validated successfully")
                    
                except Exception as model_error:
                    # If the specific model fails, try to find a working model
                    error_msg = str(model_error).lower()
                    if "not supported by any provider" in error_msg or "model not found" in error_msg:
                        logger.warning(f"Configured model '{self.model}' not available. Attempting to find alternative.")
                        
                        # Try popular models that are likely to work
                        fallback_models = [
                            "meta-llama/Llama-3.2-1B-Instruct",
                            "Qwen/Qwen2-7B-Instruct", 
                            "meta-llama/Llama-3.1-8B-Instruct"
                        ]
                        
                        for fallback_model in fallback_models:
                            try:
                                if self.provider in ["novita", "hf-inference"]:
                                    test_response = self.client.chat.completions.create(
                                        messages=[{"role": "user", "content": "Hi"}],
                                        model=fallback_model,
                                        max_tokens=1
                                    )
                                else:
                                    test_response = self.client.chat_completion(
                                        messages=[{"role": "user", "content": "Hi"}],
                                        model=fallback_model,
                                        max_tokens=1
                                    )
                                self.model = fallback_model
                                logger.info(f"Successfully switched to fallback model: {self.model}")
                                break
                            except Exception:
                                continue
                        else:
                            # If no fallback works, provider setup might be needed
                            logger.error(f"No compatible models found. Check provider setup at https://hf.co/settings/inference-providers")
                            return False
                    else:
                        logger.warning(f"Model test failed but continuing: {model_error}")
                
                self._initialized = True
                logger.info(f"HuggingFace provider initialized - Model: {self.model}, Provider: {self.provider}")
                return True
                
            except ImportError:
                logger.error("huggingface_hub library not available. Please install: pip install huggingface_hub")
                return False
            
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace provider: {str(e)}")
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
        """Complete a prompt using HuggingFace Inference Providers API"""
        if not self._initialized or not self.client:
            raise AIProviderError("HuggingFace provider not initialized")
            
        try:
            # Prepare messages for chat completions API
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Handle JSON response format request
            user_content = prompt
            if response_format and response_format.get("type") == "json_object":
                user_content += "\n\nPlease respond in valid JSON format."
            
            messages.append({"role": "user", "content": user_content})
            
            # Use InferenceClient for the request with timeout
            try:
                # Create a timeout of 15 seconds for HuggingFace API calls
                if self.provider in ["novita", "hf-inference"]:
                    # Use the new API pattern for novita and hf-inference
                    completion = await asyncio.wait_for(
                        asyncio.create_task(
                            asyncio.to_thread(
                                self.client.chat.completions.create,
                                messages=messages,
                                model=self.model,
                                max_tokens=max_tokens,
                                temperature=temperature
                            )
                        ),
                        timeout=15.0  # 15 second timeout
                    )
                else:
                    # Use the old API pattern for other providers
                    completion = await asyncio.wait_for(
                        asyncio.create_task(
                            asyncio.to_thread(
                                self.client.chat_completion,
                                messages=messages,
                                model=self.model,
                                max_tokens=max_tokens,
                                temperature=temperature,
                                stream=False
                            )
                        ),
                        timeout=15.0  # 15 second timeout
                    )
                
                # Extract content from response
                content = completion.choices[0].message.content
                
                # For JSON responses, try to parse and re-serialize
                if response_format and response_format.get("type") == "json_object":
                    try:
                        parsed = self._parse_json_response(content)
                        content = json.dumps(parsed)
                    except:
                        # If parsing fails, keep original content
                        pass
                
                # Extract usage information if available
                usage = None
                if hasattr(completion, 'usage') and completion.usage:
                    usage = {
                        "prompt_tokens": getattr(completion.usage, 'prompt_tokens', 0),
                        "completion_tokens": getattr(completion.usage, 'completion_tokens', 0),
                        "total_tokens": getattr(completion.usage, 'total_tokens', 0)
                    }
                
                return AIResponse(
                    content=content,
                    usage=usage,
                    model=self.model,
                    provider=self.name
                )
                
            except asyncio.TimeoutError:
                logger.warning(f"HuggingFace API timeout after 15 seconds for model {self.model}")
                raise AIProviderUnavailableError("HuggingFace API request timed out after 15 seconds")
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle specific error cases
                if "not supported by any provider" in error_msg:
                    raise AIProviderUnavailableError(f"Model {self.model} not supported by enabled providers. Check https://hf.co/settings/inference-providers")
                elif "rate limit" in error_msg or "429" in error_msg:
                    raise AIProviderUnavailableError("HuggingFace rate limit exceeded")
                elif "authentication" in error_msg or "401" in error_msg:
                    raise AIProviderError("HuggingFace authentication failed - check API token")
                elif "model is loading" in error_msg or "503" in error_msg or "504" in error_msg:
                    raise AIProviderUnavailableError("Model is currently loading or gateway timeout, please try again")
                elif "timeout" in error_msg:
                    raise AIProviderUnavailableError("HuggingFace API request timed out")
                else:
                    raise AIProviderError(f"HuggingFace API error: {str(e)}")
                
        except (AIProviderError, AIProviderUnavailableError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"HuggingFace completion failed: {str(e)}")
            raise AIProviderError(f"HuggingFace completion failed: {str(e)}")
    
    async def is_available(self) -> bool:
        """Check if HuggingFace provider is available"""
        if not self._initialized:
            await self.initialize()
            
        if not self._initialized or not self.client:
            return False
            
        try:
            # Make a simple test request to verify the model is available
            test_messages = [{"role": "user", "content": "Hello"}]
            
            # Use a shorter timeout for availability check (5 seconds)
            if self.provider in ["novita", "hf-inference"]:
                completion = await asyncio.wait_for(
                    asyncio.create_task(
                        asyncio.to_thread(
                            self.client.chat.completions.create,
                            messages=test_messages,
                            model=self.model,
                            max_tokens=1,
                            temperature=0.1
                        )
                    ),
                    timeout=5.0
                )
            else:
                completion = await asyncio.wait_for(
                    asyncio.create_task(
                        asyncio.to_thread(
                            self.client.chat_completion,
                            messages=test_messages,
                            model=self.model,
                            max_tokens=1,
                            temperature=0.1
                        )
                    ),
                    timeout=5.0
                )
            
            # If we get here without exception, the service is available
            return True
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Still consider available if model is just loading, paused, or rate limited
            if any(status in error_msg for status in ["loading", "paused", "endpoint is paused", "503", "rate limit", "429"]):
                return True
            # Authentication errors mean the service is unavailable for this user
            elif "authentication" in error_msg or "401" in error_msg:
                logger.warning("HuggingFace authentication failed")
                return False
            
            logger.warning(f"HuggingFace availability check failed: {str(e)}")
            return False
    
    def get_priority(self) -> int:
        """Get provider priority - HuggingFace is highest priority (free with Pro)"""
        return 10  # Highest priority = lowest number
    
    def get_name(self) -> str:
        """Get provider name"""
        return self.name