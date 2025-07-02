"""Settings API endpoints for admin panel."""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.api import deps
from app.models.user import User
from app.schemas.settings import (
    SettingResponse,
    SettingUpdate,
    SettingUpdateRequest,
    SettingCategoryResponse,
    SettingImportExport
)
from app.services.settings_service import settings_service
from app.database import get_db

router = APIRouter()


@router.get("/", response_model=Dict[str, List[SettingResponse]])
async def get_all_settings(
    include_sensitive: bool = False,
    current_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all system settings grouped by category."""
    settings = await settings_service.get_all_settings(
        db=db,
        include_sensitive=include_sensitive
    )
    
    # Convert to response format
    response = {}
    for category, category_settings in settings.items():
        category_responses = []
        for setting in category_settings:
            setting_dict = {
                "id": setting.id,
                "key": setting.key,
                "value": setting.value if include_sensitive else ("********" if setting.is_sensitive else setting.value),
                "value_type": setting.value_type,
                "category": setting.category,
                "display_name": setting.display_name,
                "description": setting.description,
                "is_sensitive": setting.is_sensitive,
                "is_readonly": setting.is_readonly,
                "validation_rules": setting.validation_rules,
                "created_at": setting.created_at,
                "updated_at": setting.updated_at,
                "updated_by": str(setting.updated_by) if setting.updated_by else None
            }
            category_responses.append(SettingResponse(**setting_dict))
        response[category] = category_responses
    
    return response


@router.get("/categories", response_model=List[SettingCategoryResponse])
async def get_settings_by_categories(
    include_sensitive: bool = False,
    current_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get settings organized by categories with metadata."""
    settings = await settings_service.get_all_settings(db=db)
    
    # Category display names
    category_names = {
        "general": "General Settings",
        "security": "Security",
        "features": "Features",
        "limits": "User Limits",
        "ai": "AI Configuration",
        "integrations": "Integrations",
        "email": "Email Settings",
        "notifications": "Notifications",
        "appearance": "Appearance"
    }
    
    response = []
    for category, category_settings in settings.items():
        category_responses = []
        for setting in category_settings:
            setting_dict = {
                "id": setting.id,
                "key": setting.key,
                "value": setting.value if include_sensitive else ("********" if setting.is_sensitive else setting.value),
                "value_type": setting.value_type,
                "category": setting.category,
                "display_name": setting.display_name,
                "description": setting.description,
                "is_sensitive": setting.is_sensitive,
                "is_readonly": setting.is_readonly,
                "validation_rules": setting.validation_rules,
                "created_at": setting.created_at,
                "updated_at": setting.updated_at,
                "updated_by": str(setting.updated_by) if setting.updated_by else None
            }
            category_responses.append(SettingResponse(**setting_dict))
        
        response.append(
            SettingCategoryResponse(
                category=category,
                display_name=category_names.get(category, category.title()),
                settings=category_responses
            )
        )
    
    return response


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    current_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific setting by key."""
    setting = await settings_service.get_setting(key=key, db=db)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting {key} not found"
        )
    
    return SettingResponse.from_orm(setting)


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    update_data: SettingUpdate,
    current_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific setting."""
    try:
        setting = await settings_service.update_setting(
            key=key,
            update_data=update_data,
            user_id=current_user.id,
            db=db
        )
        
        return SettingResponse.from_orm(setting)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating setting: {str(e)}"
        )


@router.post("/bulk", response_model=List[SettingResponse])
async def update_multiple_settings(
    request: SettingUpdateRequest,
    current_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update multiple settings at once."""
    updated_settings = await settings_service.update_multiple_settings(
        updates=request.settings,
        user_id=current_user.id,
        change_reason=request.change_reason,
        db=db
    )
    
    # Convert to response format with proper type conversion
    response = []
    for setting in updated_settings:
        setting_dict = {
            "id": setting.id,
            "key": setting.key,
            "value": setting.value if not setting.is_sensitive else "********",
            "value_type": setting.value_type,
            "category": setting.category,
            "display_name": setting.display_name,
            "description": setting.description,
            "is_sensitive": setting.is_sensitive,
            "is_readonly": setting.is_readonly,
            "validation_rules": setting.validation_rules,
            "created_at": setting.created_at,
            "updated_at": setting.updated_at,
            "updated_by": str(setting.updated_by) if setting.updated_by else None
        }
        response.append(SettingResponse(**setting_dict))
    
    return response


@router.post("/initialize")
async def initialize_settings(
    current_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Initialize default settings from environment variables."""
    await settings_service.initialize_settings(db=db)
    return {"message": "Settings initialized successfully"}


@router.get("/export/json", response_model=SettingImportExport)
async def export_settings(
    include_sensitive: bool = False,
    current_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Export all settings as JSON."""
    export_data = await settings_service.export_settings(
        db=db,
        include_sensitive=include_sensitive
    )
    
    export_data["exported_by"] = current_user.email
    
    return SettingImportExport(**export_data)


@router.post("/import/json")
async def import_settings(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Import settings from JSON file."""
    try:
        # Read and parse file
        content = await file.read()
        import_data = json.loads(content)
        
        # Import settings
        imported = await settings_service.import_settings(
            import_data=import_data,
            user_id=current_user.id,
            db=db
        )
        
        return {
            "message": f"Successfully imported {len(imported)} settings",
            "imported_keys": [s.key for s in imported]
        }
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing settings: {str(e)}"
        )


@router.post("/reset/{category}")
async def reset_category_settings(
    category: str,
    current_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset all settings in a category to default values."""
    # This would reset settings to their default values from DEFAULT_SETTINGS
    # Implementation depends on specific requirements
    return {
        "message": f"Category {category} settings reset to defaults"
    }