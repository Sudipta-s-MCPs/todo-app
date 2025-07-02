"""Settings-related Pydantic schemas."""
from datetime import datetime
from typing import Optional, Any, Dict, List
from uuid import UUID
from pydantic import BaseModel, Field, validator
import json


class SettingBase(BaseModel):
    """Base schema for settings."""
    key: str = Field(..., min_length=1, max_length=255)
    value: Optional[str] = None
    value_type: str = Field(default="string", pattern="^(string|int|float|bool|json)$")
    category: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_sensitive: bool = False
    is_readonly: bool = False
    validation_rules: Optional[Dict[str, Any]] = None


class SettingCreate(SettingBase):
    """Schema for creating a setting."""
    pass


class SettingUpdate(BaseModel):
    """Schema for updating a setting value."""
    value: str
    change_reason: Optional[str] = None
    
    @validator('value')
    def validate_value_not_empty(cls, v):
        if v is None or v == "":
            raise ValueError("Value cannot be empty")
        return v


class SettingResponse(SettingBase):
    """Schema for setting response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class SettingUpdateRequest(BaseModel):
    """Request to update multiple settings at once."""
    settings: Dict[str, str] = Field(..., description="Key-value pairs of settings to update")
    change_reason: Optional[str] = None


class SettingCategoryResponse(BaseModel):
    """Response for settings grouped by category."""
    category: str
    display_name: str
    settings: List[SettingResponse]


class SettingImportExport(BaseModel):
    """Schema for importing/exporting settings."""
    settings: Dict[str, Any]
    exported_at: Optional[datetime] = None
    exported_by: Optional[str] = None
    version: str = "1.0"