"""
Settings database models for admin panel configuration
Created: 2025-01-02 07:00:00 PST
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, JSON, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class SystemSetting(Base):
    """System-wide settings configurable from admin panel"""
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(50), nullable=False, default="string")  # string, int, float, bool, json
    category = Column(String(100), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_sensitive = Column(Boolean, default=False)  # Hide value in UI for sensitive settings
    is_readonly = Column(Boolean, default=False)  # Cannot be modified from UI
    validation_rules = Column(JSON, nullable=True)  # JSON schema for validation
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Change tracking
    previous_value = Column(Text, nullable=True)
    change_reason = Column(Text, nullable=True)


class SettingCategory:
    """Predefined setting categories"""
    GENERAL = "general"
    SECURITY = "security"
    FEATURES = "features"
    LIMITS = "limits"
    AI = "ai"
    INTEGRATIONS = "integrations"
    EMAIL = "email"
    NOTIFICATIONS = "notifications"
    APPEARANCE = "appearance"