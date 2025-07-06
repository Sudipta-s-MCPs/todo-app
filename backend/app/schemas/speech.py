"""Speech-related Pydantic schemas."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    """Schema for transcription result."""
    text: str = Field(..., description="Transcribed text")
    language: Optional[str] = Field(None, description="Detected or specified language code")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")


class VoiceMessageRequest(BaseModel):
    """Schema for voice message request (used with Form data)."""
    language: Optional[str] = Field("auto", description="Language hint: auto, en, bn, hi")


class VoiceMessageResponse(BaseModel):
    """Schema for voice message response."""
    transcription: TranscriptionResult
    chatResponse: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional chat response if message was processed",
        alias="chat_response"
    )
    
    class Config:
        populate_by_name = True


class SupportedLanguagesResponse(BaseModel):
    """Schema for supported languages response."""
    languages: Dict[str, str] = Field(..., description="Map of language code to display name")


class SpeechUsageResponse(BaseModel):
    """Schema for speech API usage statistics."""
    transcriptions_today: int = Field(..., description="Number of transcriptions today")
    minutes_processed: float = Field(..., description="Total minutes of audio processed")
    last_transcription: Optional[str] = Field(None, description="Timestamp of last transcription")