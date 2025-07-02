"""Chat API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatResponse,
    CommandExecute,
    AIUsageResponse,
    ChatConversationResponse
)
from app.services.chat_service import chat_service
from app.database import get_db

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessageCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message and get AI response."""
    try:
        result = await chat_service.process_message(
            content=message.content,
            user_id=current_user.id,
            conversation_id=message.conversation_id,
            db=db
        )
        
        # Convert internal format to response format
        return ChatResponse(
            message=result["message"],
            conversation_id=result["conversationId"],
            tasks=result.get("tasks", []),
            action=result.get("action"),
            used_ai=result["usedAI"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.post("/execute", response_model=ChatResponse)
async def execute_command(
    command: CommandExecute,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute a pattern-based command without AI."""
    # Format as command for pattern matching
    formatted_command = f"{command.command} {command.args}".strip()
    
    try:
        result = await chat_service.process_message(
            content=formatted_command,
            user_id=current_user.id,
            conversation_id=None,
            db=db
        )
        
        return ChatResponse(
            message=result["message"],
            conversation_id=result["conversationId"],
            tasks=result.get("tasks", []),
            action=result.get("action"),
            used_ai=False
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing command: {str(e)}"
        )


@router.get("/conversations", response_model=List[ChatConversationResponse])
async def get_conversations(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's chat conversations."""
    conversations = await chat_service.get_conversations(
        user_id=current_user.id,
        db=db
    )
    return conversations


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a specific conversation."""
    messages = await chat_service.get_conversation_messages(
        conversation_id=conversation_id,
        user_id=current_user.id,
        db=db
    )
    return messages


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation."""
    # For now, just return success as we don't persist conversations
    return {"message": "Conversation deleted"}


@router.get("/ai-usage", response_model=AIUsageResponse)
async def get_ai_usage(
    current_user: User = Depends(deps.get_current_user)
):
    """Get user's AI usage statistics."""
    usage = await chat_service.get_ai_usage(user_id=current_user.id)
    return AIUsageResponse(**usage)