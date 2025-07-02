"""Chat-related Pydantic schemas."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ChatMessageBase(BaseModel):
    """Base schema for chat messages."""
    content: str = Field(..., min_length=1, max_length=1000)


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a chat message."""
    conversation_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Schema for chat message response."""
    id: str
    content: str
    sender: Literal["user", "assistant"]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ChatConversationResponse(BaseModel):
    """Schema for chat conversation response."""
    id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Schema for chat response."""
    message: ChatMessageResponse
    conversationId: Optional[str] = Field(None, alias="conversation_id")
    tasks: Optional[List[Dict[str, Any]]] = None
    action: Optional[str] = None
    usedAI: bool = Field(alias="used_ai")

    class Config:
        populate_by_name = True


class CommandExecute(BaseModel):
    """Schema for command execution."""
    command: str = Field(..., min_length=1, max_length=50)
    args: str = Field(..., max_length=500)


class AIUsageResponse(BaseModel):
    """Schema for AI usage response."""
    used: int
    limit: int