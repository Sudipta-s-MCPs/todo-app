"""Settings service for managing system configuration."""
import json
import os
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from app.models.settings import SystemSetting, SettingCategory
from app.schemas.settings import SettingCreate, SettingUpdate
from app.config import settings as env_settings
from app.services.cache import get_redis_client
import logging

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing system settings."""
    
    # Default settings to initialize from environment
    DEFAULT_SETTINGS = [
        # Security Settings
        {
            "key": "enable_rate_limiting",
            "value": os.getenv("ENABLE_RATE_LIMITING", "true"),
            "value_type": "bool",
            "category": SettingCategory.SECURITY,
            "display_name": "Enable Rate Limiting",
            "description": "Enable API rate limiting for security"
        },
        {
            "key": "rate_limit_per_minute",
            "value": os.getenv("RATE_LIMIT_PER_MINUTE", "60"),
            "value_type": "int",
            "category": SettingCategory.SECURITY,
            "display_name": "Rate Limit Per Minute",
            "description": "Maximum API requests per minute per user",
            "validation_rules": {"min": 10, "max": 1000}
        },
        {
            "key": "rate_limit_per_hour",
            "value": os.getenv("RATE_LIMIT_PER_HOUR", "600"),
            "value_type": "int",
            "category": SettingCategory.SECURITY,
            "display_name": "Rate Limit Per Hour",
            "description": "Maximum API requests per hour per user",
            "validation_rules": {"min": 100, "max": 10000}
        },
        {
            "key": "rate_limit_burst",
            "value": os.getenv("RATE_LIMIT_BURST", "10"),
            "value_type": "int",
            "category": SettingCategory.SECURITY,
            "display_name": "Rate Limit Burst",
            "description": "Burst allowance for rate limiting",
            "validation_rules": {"min": 1, "max": 100}
        },
        {
            "key": "enable_request_validation",
            "value": os.getenv("ENABLE_REQUEST_VALIDATION", "true"),
            "value_type": "bool",
            "category": SettingCategory.SECURITY,
            "display_name": "Enable Request Validation",
            "description": "Enable strict request validation"
        },
        {
            "key": "enable_security_headers",
            "value": os.getenv("ENABLE_SECURITY_HEADERS", "true"),
            "value_type": "bool",
            "category": SettingCategory.SECURITY,
            "display_name": "Enable Security Headers",
            "description": "Enable security headers in responses"
        },
        {
            "key": "enable_audit_logging",
            "value": os.getenv("ENABLE_AUDIT_LOGGING", "true"),
            "value_type": "bool",
            "category": SettingCategory.SECURITY,
            "display_name": "Enable Audit Logging",
            "description": "Enable detailed audit logging"
        },
        {
            "key": "admin_ip_whitelist",
            "value": os.getenv("ADMIN_IP_WHITELIST", ""),
            "value_type": "string",
            "category": SettingCategory.SECURITY,
            "display_name": "Admin IP Whitelist",
            "description": "Comma-separated list of allowed IPs for admin access"
        },
        
        # Feature Flags
        {
            "key": "mfa_enabled",
            "value": os.getenv("MFA_ENABLED", "true"),
            "value_type": "bool",
            "category": SettingCategory.FEATURES,
            "display_name": "Enable Two-Factor Authentication",
            "description": "Allow users to enable 2FA for their accounts"
        },
        {
            "key": "api_keys_enabled",
            "value": os.getenv("API_KEYS_ENABLED", "true"),
            "value_type": "bool",
            "category": SettingCategory.FEATURES,
            "display_name": "Enable API Keys",
            "description": "Allow users to create API keys"
        },
        {
            "key": "websockets_enabled",
            "value": os.getenv("WEBSOCKETS_ENABLED", "true"),
            "value_type": "bool",
            "category": SettingCategory.FEATURES,
            "display_name": "Enable WebSockets",
            "description": "Enable real-time updates via WebSockets"
        },
        
        # User Limits
        {
            "key": "max_workspaces_per_user",
            "value": os.getenv("MAX_WORKSPACES_PER_USER", "10"),
            "value_type": "int",
            "category": SettingCategory.LIMITS,
            "display_name": "Max Workspaces Per User",
            "description": "Maximum number of workspaces a user can create",
            "validation_rules": {"min": 1, "max": 100}
        },
        {
            "key": "max_tasks_per_list",
            "value": os.getenv("MAX_TASKS_PER_LIST", "1000"),
            "value_type": "int",
            "category": SettingCategory.LIMITS,
            "display_name": "Max Tasks Per List",
            "description": "Maximum number of tasks in a single list",
            "validation_rules": {"min": 100, "max": 10000}
        },
        {
            "key": "max_lists_per_workspace",
            "value": os.getenv("MAX_LISTS_PER_WORKSPACE", "50"),
            "value_type": "int",
            "category": SettingCategory.LIMITS,
            "display_name": "Max Lists Per Workspace",
            "description": "Maximum number of lists in a workspace",
            "validation_rules": {"min": 10, "max": 500}
        },
        {
            "key": "max_api_keys_per_user",
            "value": os.getenv("MAX_API_KEYS_PER_USER", "5"),
            "value_type": "int",
            "category": SettingCategory.LIMITS,
            "display_name": "Max API Keys Per User",
            "description": "Maximum number of API keys per user",
            "validation_rules": {"min": 1, "max": 20}
        },
        {
            "key": "max_devices_per_user",
            "value": os.getenv("MAX_DEVICES_PER_USER", "10"),
            "value_type": "int",
            "category": SettingCategory.LIMITS,
            "display_name": "Max Devices Per User",
            "description": "Maximum number of devices per user",
            "validation_rules": {"min": 1, "max": 50}
        },
        
        # AI Settings
        {
            "key": "groq_api_key",
            "value": os.getenv("GROQ_API_KEY", ""),
            "value_type": "string",
            "category": SettingCategory.AI,
            "display_name": "Groq API Key",
            "description": "API key for Groq AI service",
            "is_sensitive": True
        },
        {
            "key": "groq_model",
            "value": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "value_type": "string",
            "category": SettingCategory.AI,
            "display_name": "AI Model",
            "description": "Groq model to use for AI features"
        },
        {
            "key": "ai_daily_token_limit",
            "value": os.getenv("AI_DAILY_TOKEN_LIMIT", "20000"),
            "value_type": "int",
            "category": SettingCategory.AI,
            "display_name": "Daily AI Token Limit",
            "description": "Maximum AI tokens per day (system-wide)",
            "validation_rules": {"min": 1000, "max": 1000000}
        },
        {
            "key": "enable_ai_duplicate_detection",
            "value": os.getenv("ENABLE_AI_DUPLICATE_DETECTION", "true"),
            "value_type": "bool",
            "category": SettingCategory.AI,
            "display_name": "Enable AI Duplicate Detection",
            "description": "Use AI to enhance duplicate task detection"
        },
        {
            "key": "ai_temperature",
            "value": os.getenv("AI_TEMPERATURE", "0.3"),
            "value_type": "float",
            "category": SettingCategory.AI,
            "display_name": "AI Temperature",
            "description": "Temperature setting for AI responses (0.0-1.0)",
            "validation_rules": {"min": 0.0, "max": 1.0}
        },
        {
            "key": "ai_max_tokens",
            "value": os.getenv("AI_MAX_TOKENS", "500"),
            "value_type": "int",
            "category": SettingCategory.AI,
            "display_name": "AI Max Tokens",
            "description": "Maximum tokens per AI response",
            "validation_rules": {"min": 100, "max": 2000}
        },
        {
            "key": "ai_cache_ttl",
            "value": os.getenv("AI_CACHE_TTL", "86400"),
            "value_type": "int",
            "category": SettingCategory.AI,
            "display_name": "AI Cache TTL",
            "description": "AI response cache time-to-live in seconds",
            "validation_rules": {"min": 300, "max": 604800}
        },
        {
            "key": "ai_user_monthly_token_limit",
            "value": os.getenv("AI_USER_MONTHLY_TOKEN_LIMIT", "50000"),
            "value_type": "int",
            "category": SettingCategory.AI,
            "display_name": "AI User Monthly Token Limit",
            "description": "Maximum AI tokens per user per month",
            "validation_rules": {"min": 1000, "max": 1000000}
        },
        
        # Integration Settings - LDAP
        {
            "key": "ldap_enabled",
            "value": os.getenv("LDAP_ENABLED", "false"),
            "value_type": "bool",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "Enable LDAP Authentication",
            "description": "Enable LDAP/Active Directory authentication"
        },
        {
            "key": "ldap_server",
            "value": os.getenv("LDAP_SERVER", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Server",
            "description": "LDAP server hostname or IP"
        },
        {
            "key": "ldap_port",
            "value": os.getenv("LDAP_PORT", "389"),
            "value_type": "int",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Port",
            "description": "LDAP server port (389 for standard, 636 for SSL)",
            "validation_rules": {"min": 1, "max": 65535}
        },
        {
            "key": "ldap_use_ssl",
            "value": os.getenv("LDAP_USE_SSL", "false"),
            "value_type": "bool",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Use SSL",
            "description": "Use SSL for LDAP connection"
        },
        {
            "key": "ldap_start_tls",
            "value": os.getenv("LDAP_START_TLS", "true"),
            "value_type": "bool",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Start TLS",
            "description": "Use StartTLS for LDAP connection"
        },
        {
            "key": "ldap_bind_dn",
            "value": os.getenv("LDAP_BIND_DN", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Bind DN",
            "description": "Distinguished name for LDAP bind",
            "is_sensitive": True
        },
        {
            "key": "ldap_bind_password",
            "value": os.getenv("LDAP_BIND_PASSWORD", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Bind Password",
            "description": "Password for LDAP bind",
            "is_sensitive": True
        },
        {
            "key": "ldap_base_dn",
            "value": os.getenv("LDAP_BASE_DN", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Base DN",
            "description": "Base distinguished name for LDAP searches"
        },
        {
            "key": "ldap_user_dn_template",
            "value": os.getenv("LDAP_USER_DN_TEMPLATE", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP User DN Template",
            "description": "Template for user DN (e.g., uid={username},cn=users,dc=example,dc=com)"
        },
        {
            "key": "ldap_user_search_base",
            "value": os.getenv("LDAP_USER_SEARCH_BASE", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP User Search Base",
            "description": "Search base for user lookup"
        },
        {
            "key": "ldap_user_filter",
            "value": os.getenv("LDAP_USER_FILTER", "(objectClass=inetOrgPerson)"),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP User Filter",
            "description": "LDAP filter for user objects"
        },
        {
            "key": "ldap_user_attr_email",
            "value": os.getenv("LDAP_USER_ATTR_EMAIL", "mail"),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Email Attribute",
            "description": "LDAP attribute for user email"
        },
        {
            "key": "ldap_user_attr_name",
            "value": os.getenv("LDAP_USER_ATTR_NAME", "displayName"),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Name Attribute",
            "description": "LDAP attribute for user display name"
        },
        {
            "key": "ldap_user_attr_uid",
            "value": os.getenv("LDAP_USER_ATTR_UID", "uid"),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP UID Attribute",
            "description": "LDAP attribute for user ID"
        },
        {
            "key": "ldap_group_search_base",
            "value": os.getenv("LDAP_GROUP_SEARCH_BASE", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Group Search Base",
            "description": "Search base for group lookup"
        },
        {
            "key": "ldap_group_filter",
            "value": os.getenv("LDAP_GROUP_FILTER", "(objectClass=groupOfNames)"),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Group Filter",
            "description": "LDAP filter for group objects"
        },
        {
            "key": "ldap_connection_timeout",
            "value": os.getenv("LDAP_CONNECTION_TIMEOUT", "5"),
            "value_type": "int",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Connection Timeout",
            "description": "Connection timeout for LDAP in seconds",
            "validation_rules": {"min": 1, "max": 60}
        },
        {
            "key": "ldap_auto_create_user",
            "value": os.getenv("LDAP_AUTO_CREATE_USER", "true"),
            "value_type": "bool",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Auto Create User",
            "description": "Automatically create users from LDAP authentication"
        },
        {
            "key": "ldap_ignore_tls_errors",
            "value": os.getenv("LDAP_IGNORE_TLS_ERRORS", "true"),
            "value_type": "bool",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "LDAP Ignore TLS Errors",
            "description": "Ignore TLS certificate errors for LDAP"
        },
        
        # Integration Settings - MinIO
        {
            "key": "minio_endpoint",
            "value": os.getenv("MINIO_ENDPOINT", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "MinIO Endpoint",
            "description": "MinIO server endpoint for file storage"
        },
        {
            "key": "minio_access_key",
            "value": os.getenv("MINIO_ACCESS_KEY", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "MinIO Access Key",
            "description": "MinIO access key for authentication",
            "is_sensitive": True
        },
        {
            "key": "minio_secret_key",
            "value": os.getenv("MINIO_SECRET_KEY", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "MinIO Secret Key",
            "description": "MinIO secret key for authentication",
            "is_sensitive": True
        },
        {
            "key": "minio_secure",
            "value": os.getenv("MINIO_SECURE", "false"),
            "value_type": "bool",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "MinIO Use HTTPS",
            "description": "Use HTTPS for MinIO connections"
        },
        {
            "key": "minio_bucket_name",
            "value": os.getenv("MINIO_BUCKET_NAME", "smart-todo"),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "MinIO Bucket Name",
            "description": "Default bucket name for file storage"
        },
        
        # Integration Settings - Qdrant
        {
            "key": "qdrant_host",
            "value": os.getenv("QDRANT_HOST", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "Qdrant Host",
            "description": "Qdrant vector database host"
        },
        {
            "key": "qdrant_port",
            "value": os.getenv("QDRANT_PORT", "6333"),
            "value_type": "int",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "Qdrant Port",
            "description": "Qdrant vector database port",
            "validation_rules": {"min": 1, "max": 65535}
        },
        {
            "key": "qdrant_api_key",
            "value": os.getenv("QDRANT_API_KEY", ""),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "Qdrant API Key",
            "description": "API key for Qdrant authentication",
            "is_sensitive": True
        },
        {
            "key": "qdrant_collection_name",
            "value": os.getenv("QDRANT_COLLECTION_NAME", "smart_todo_tasks"),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "Qdrant Collection Name",
            "description": "Default collection name for vector storage"
        },
        {
            "key": "qdrant_embedding_model",
            "value": os.getenv("QDRANT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            "value_type": "string",
            "category": SettingCategory.INTEGRATIONS,
            "display_name": "Qdrant Embedding Model",
            "description": "Model used for generating embeddings"
        }
    ]
    
    def __init__(self):
        self.cache = get_redis_client()
        self.cache_ttl = 300  # 5 minutes
    
    async def initialize_settings(self, db: AsyncSession) -> None:
        """Initialize default settings from environment variables."""
        try:
            for setting_data in self.DEFAULT_SETTINGS:
                # Check if setting already exists
                existing = await db.execute(
                    select(SystemSetting).where(SystemSetting.key == setting_data["key"])
                )
                if existing.scalar_one_or_none():
                    continue
                
                # Create new setting
                setting = SystemSetting(**setting_data)
                db.add(setting)
            
            await db.commit()
            logger.info("System settings initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing settings: {str(e)}")
            await db.rollback()
    
    async def get_setting(
        self, 
        key: str, 
        db: AsyncSession,
        use_cache: bool = True
    ) -> Optional[SystemSetting]:
        """Get a single setting by key."""
        # Check cache first
        if use_cache and self.cache:
            cached = await self.cache.get(f"setting:{key}")
            if cached:
                return json.loads(cached)
        
        # Get from database
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        # Cache the result
        if setting and self.cache and use_cache:
            await self.cache.setex(
                f"setting:{key}",
                self.cache_ttl,
                json.dumps(setting.dict() if hasattr(setting, 'dict') else {})
            )
        
        return setting
    
    async def get_settings_by_category(
        self, 
        category: str,
        db: AsyncSession
    ) -> List[SystemSetting]:
        """Get all settings for a category."""
        result = await db.execute(
            select(SystemSetting)
            .where(SystemSetting.category == category)
            .order_by(SystemSetting.display_name)
        )
        return result.scalars().all()
    
    async def get_all_settings(
        self,
        db: AsyncSession,
        include_sensitive: bool = False
    ) -> Dict[str, List[SystemSetting]]:
        """Get all settings grouped by category."""
        query = select(SystemSetting).order_by(
            SystemSetting.category,
            SystemSetting.display_name
        )
        
        # Always include sensitive settings - they will be masked in the API response
        
        result = await db.execute(query)
        settings = result.scalars().all()
        
        # Group by category
        grouped = {}
        for setting in settings:
            if setting.category not in grouped:
                grouped[setting.category] = []
            grouped[setting.category].append(setting)
        
        return grouped
    
    async def update_setting(
        self,
        key: str,
        update_data: SettingUpdate,
        user_id: str,
        db: AsyncSession
    ) -> SystemSetting:
        """Update a setting value."""
        setting = await self.get_setting(key, db, use_cache=False)
        if not setting:
            raise ValueError(f"Setting {key} not found")
        
        if setting.is_readonly:
            raise ValueError(f"Setting {key} is read-only")
        
        # Validate value based on type
        validated_value = self._validate_value(
            update_data.value,
            setting.value_type,
            setting.validation_rules
        )
        
        # Store previous value
        setting.previous_value = setting.value
        setting.value = validated_value
        setting.updated_by = user_id
        setting.change_reason = update_data.change_reason
        setting.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(setting)
        
        # Clear cache
        if self.cache:
            await self.cache.delete(f"setting:{key}")
        
        return setting
    
    async def update_multiple_settings(
        self,
        updates: Dict[str, str],
        user_id: str,
        change_reason: Optional[str],
        db: AsyncSession
    ) -> List[SystemSetting]:
        """Update multiple settings at once."""
        updated_settings = []
        
        for key, value in updates.items():
            try:
                setting = await self.update_setting(
                    key=key,
                    update_data=SettingUpdate(
                        value=value,
                        change_reason=change_reason
                    ),
                    user_id=user_id,
                    db=db
                )
                updated_settings.append(setting)
            except Exception as e:
                logger.error(f"Error updating setting {key}: {str(e)}")
                # Continue with other settings
        
        return updated_settings
    
    def _validate_value(
        self, 
        value: str, 
        value_type: str,
        validation_rules: Optional[Dict[str, Any]]
    ) -> str:
        """Validate and convert setting value based on type."""
        try:
            if value_type == "int":
                int_val = int(value)
                if validation_rules:
                    if "min" in validation_rules and int_val < validation_rules["min"]:
                        raise ValueError(f"Value must be at least {validation_rules['min']}")
                    if "max" in validation_rules and int_val > validation_rules["max"]:
                        raise ValueError(f"Value must be at most {validation_rules['max']}")
                return str(int_val)
            
            elif value_type == "float":
                float_val = float(value)
                if validation_rules:
                    if "min" in validation_rules and float_val < validation_rules["min"]:
                        raise ValueError(f"Value must be at least {validation_rules['min']}")
                    if "max" in validation_rules and float_val > validation_rules["max"]:
                        raise ValueError(f"Value must be at most {validation_rules['max']}")
                return str(float_val)
            
            elif value_type == "bool":
                bool_val = value.lower() in ("true", "1", "yes", "on")
                return str(bool_val).lower()
            
            elif value_type == "json":
                # Validate JSON
                json.loads(value)
                return value
            
            else:  # string
                if validation_rules:
                    if "pattern" in validation_rules:
                        import re
                        if not re.match(validation_rules["pattern"], value):
                            raise ValueError(f"Value must match pattern: {validation_rules['pattern']}")
                    if "max_length" in validation_rules and len(value) > validation_rules["max_length"]:
                        raise ValueError(f"Value must be at most {validation_rules['max_length']} characters")
                return value
                
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid value for type {value_type}: {str(e)}")
    
    async def export_settings(
        self,
        db: AsyncSession,
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """Export all settings for backup."""
        settings = await self.get_all_settings(db, include_sensitive)
        
        export_data = {}
        for category, category_settings in settings.items():
            for setting in category_settings:
                if not include_sensitive and setting.is_sensitive:
                    continue
                export_data[setting.key] = {
                    "value": setting.value,
                    "type": setting.value_type,
                    "category": setting.category
                }
        
        return {
            "settings": export_data,
            "exported_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
    
    async def import_settings(
        self,
        import_data: Dict[str, Any],
        user_id: str,
        db: AsyncSession
    ) -> List[SystemSetting]:
        """Import settings from backup."""
        if "settings" not in import_data:
            raise ValueError("Invalid import data format")
        
        imported_settings = []
        for key, data in import_data["settings"].items():
            try:
                setting = await self.get_setting(key, db)
                if setting and not setting.is_readonly:
                    await self.update_setting(
                        key=key,
                        update_data=SettingUpdate(
                            value=data["value"],
                            change_reason=f"Imported from backup"
                        ),
                        user_id=user_id,
                        db=db
                    )
                    imported_settings.append(setting)
            except Exception as e:
                logger.error(f"Error importing setting {key}: {str(e)}")
        
        return imported_settings


# Global settings service instance
settings_service = SettingsService()