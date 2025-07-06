"""
Speech Service for handling audio transcription using HuggingFace Inference API
Created: 2025-07-06
"""

import base64
from huggingface_hub import InferenceClient
from typing import Optional, Dict, Any, Tuple
import logging
from io import BytesIO
import tempfile
import os

from app.services.dynamic_settings import dynamic_settings
from app.services.cache import get_redis_client
from app.utils.logging import get_logger

logger = get_logger(__name__)

class SpeechService:
    """Service for handling speech-to-text using HuggingFace Inference API"""
    
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache for transcriptions
        
    async def transcribe_audio(
        self,
        audio_data: bytes,
        language_hint: Optional[str] = None,
        model: str = "openai/whisper-large-v3"
    ) -> Dict[str, Any]:
        """
        Transcribe audio using HuggingFace Whisper API
        
        Args:
            audio_data: Audio file bytes
            language_hint: Optional language code (en, bn, hi, auto)
            model: Whisper model to use (whisper-tiny, whisper-large-v3, etc.)
            
        Returns:
            Dict with transcription results
        """
        try:
            # Get HuggingFace API token
            hf_token = dynamic_settings.HUGGINGFACE_API_TOKEN
            if not hf_token:
                logger.error("HuggingFace API token not configured")
                return {
                    "text": "",
                    "error": "Speech service not configured",
                    "language": None,
                    "confidence": 0.0
                }
            
            # The InferenceClient expects audio as a file path, BytesIO, or URL
            # We'll use a temporary file approach for reliability
            
            # Detect audio format from magic bytes
            file_extension, mime_type = self._detect_audio_format(audio_data)
            
            # Create InferenceClient with appropriate content type header
            client = InferenceClient(
                provider="hf-inference",
                api_key=hf_token,
                headers={"Content-Type": mime_type}
            )
            
            # Create a temporary file with the appropriate extension
            with tempfile.NamedTemporaryFile(
                suffix=f".{file_extension}", 
                delete=False
            ) as temp_audio_file:
                temp_audio_file.write(audio_data)
                temp_audio_file.flush()
                temp_file_path = temp_audio_file.name
            
            try:
                # Perform automatic speech recognition using the file path
                result = client.automatic_speech_recognition(
                    audio=temp_file_path,
                    model=model
                )
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
            # Extract text from the result
            # The result is an AutomaticSpeechRecognitionOutput object with a 'text' attribute
            transcribed_text = result.text if hasattr(result, 'text') else str(result)
            
            # Try to detect language if not specified
            detected_language = language_hint if language_hint else "auto"
            
            return {
                "text": transcribed_text.strip(),
                "language": detected_language,
                "confidence": 0.95,  # Default confidence since new API doesn't provide it
                "error": None
            }
                    
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in speech transcription: {error_msg}")
            
            # Handle specific error cases
            if "401" in error_msg or "authentication" in error_msg.lower():
                return {
                    "text": "",
                    "error": "Authentication failed - check HuggingFace API token",
                    "language": None,
                    "confidence": 0.0
                }
            elif "model is currently loading" in error_msg.lower():
                return {
                    "text": "",
                    "error": "Model is loading, please try again in a few seconds",
                    "language": None,
                    "confidence": 0.0
                }
            elif "timeout" in error_msg.lower():
                return {
                    "text": "",
                    "error": "Transcription timeout - audio too long",
                    "language": None,
                    "confidence": 0.0
                }
            else:
                return {
                    "text": "",
                    "error": f"Transcription failed: {error_msg}",
                    "language": None,
                    "confidence": 0.0
                }
    
    def _detect_audio_format(self, audio_data: bytes) -> Tuple[str, str]:
        """
        Detect audio format from magic bytes and return extension and MIME type
        
        Returns:
            Tuple of (file extension without dot, MIME type)
        """
        # Check for common audio formats by their magic bytes
        if audio_data.startswith(b'RIFF') and b'WAVE' in audio_data[:12]:
            return "wav", "audio/wav"
        elif audio_data.startswith(b'\x1a\x45\xdf\xa3'):
            # WebM format
            return "webm", "audio/webm"
        elif audio_data.startswith(b'OggS'):
            return "ogg", "audio/ogg"
        elif audio_data[:4] in [b'fLaC', b'ID3\x03', b'ID3\x04']:
            return "flac", "audio/flac"
        elif audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
            return "mp3", "audio/mpeg"
        elif audio_data[:4] == b'\x00\x00\x00\x20' and audio_data[4:8] == b'ftyp':
            return "m4a", "audio/x-m4a"
        else:
            # Default to webm as that's what the browser typically sends
            return "webm", "audio/webm"
    
    def _normalize_language_code(self, language: str) -> str:
        """Normalize language codes from various formats"""
        language = language.lower().strip()
        
        # Map various formats to our standard codes
        lang_map = {
            "english": "en",
            "en": "en",
            "eng": "en",
            "hindi": "hi", 
            "hi": "hi",
            "hin": "hi",
            "bengali": "bn",
            "bn": "bn",
            "ben": "bn",
            "bangla": "bn",
        }
        
        return lang_map.get(language, language)
    
    async def validate_audio_format(self, audio_data: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate that audio is in a supported format
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check minimum size (at least 1KB)
            if len(audio_data) < 1024:
                return False, "Audio file too small"
            
            # Check maximum size (10MB)
            if len(audio_data) > 10 * 1024 * 1024:
                return False, "Audio file too large (max 10MB)"
            
            # Try to detect format from magic bytes
            if audio_data.startswith(b'RIFF') and b'WAVE' in audio_data[:12]:
                # WAV format - ideal
                return True, None
            elif audio_data.startswith(b'\x1a\x45\xdf\xa3'):
                # WebM format - acceptable
                return True, None
            elif audio_data.startswith(b'OggS'):
                # Ogg format - acceptable
                return True, None
            else:
                # Try to detect by other means or accept as-is
                # HuggingFace API is quite flexible with formats
                return True, None
                
        except Exception as e:
            logger.error(f"Error validating audio format: {str(e)}")
            return False, "Invalid audio format"
    
    async def convert_webm_to_wav(self, webm_data: bytes) -> Optional[bytes]:
        """
        Convert WebM audio to WAV format if needed
        Note: This is a placeholder - actual conversion would require 
        ffmpeg or similar tool
        """
        # For now, we'll let HuggingFace handle the WebM format directly
        # as it supports multiple audio formats
        return webm_data
    
    async def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages for speech recognition"""
        return {
            "auto": "Auto-detect",
            "en": "English",
            "hi": "Hindi (हिन्दी)",
            "bn": "Bengali (বাংলা)",
            # Whisper supports 100+ languages, but we focus on these three
        }
    
    async def get_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get speech API usage statistics for a user"""
        redis_client = get_redis_client()
        if not redis_client:
            return {
                "transcriptions_today": 0,
                "minutes_processed": 0,
                "last_transcription": None
            }
        
        try:
            # Implementation would track usage in Redis
            # For now, return placeholder
            return {
                "transcriptions_today": 0,
                "minutes_processed": 0,
                "last_transcription": None
            }
        except Exception as e:
            logger.error(f"Error getting speech usage stats: {str(e)}")
            return {
                "transcriptions_today": 0,
                "minutes_processed": 0,
                "last_transcription": None
            }


# Singleton instance
_speech_service: Optional[SpeechService] = None


def get_speech_service() -> SpeechService:
    """Get or create speech service instance"""
    global _speech_service
    if _speech_service is None:
        _speech_service = SpeechService()
    return _speech_service