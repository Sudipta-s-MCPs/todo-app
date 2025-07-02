"""
Chat-related database models
Created: 2025-01-02 13:00:00 PST
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ChatMessage(Base):
    """Chat messages between users and AI assistant"""
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    sender = Column(String(20), nullable=False)  # 'user' or 'assistant'
    message_metadata = Column(JSON, nullable=True)  # For AI usage, action type, task references, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="chat_messages")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_chat_messages_user_timestamp", "user_id", "created_at"),
        Index("idx_chat_messages_user_sender", "user_id", "sender"),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, user_id={self.user_id}, sender={self.sender})>"