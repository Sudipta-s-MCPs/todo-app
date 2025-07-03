"""
Dynamic settings service that loads configuration from database
Created: 2025-07-02 17:00:00 PST
"""

from typing import Dict, Any, Optional
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.settings import SystemSetting
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DynamicSettings:
    """Service for accessing settings dynamically from database"""
    
    def __init__(self):
        self._settings_cache: Dict[str, Any] = {}
        self._loaded = False
        
    async def load_settings(self, db: Optional[AsyncSession] = None):
        """Load all settings from database into cache"""
        close_db = False
        if not db:
            db = AsyncSessionLocal()
            close_db = True
            
        try:
            result = await db.execute(select(SystemSetting))
            settings = result.scalars().all()
            
            for setting in settings:
                # Convert value based on type
                if setting.value_type == "bool":
                    self._settings_cache[setting.key] = setting.value.lower() == "true"
                elif setting.value_type == "int":
                    self._settings_cache[setting.key] = int(setting.value) if setting.value else 0
                elif setting.value_type == "float":
                    self._settings_cache[setting.key] = float(setting.value) if setting.value else 0.0
                else:
                    self._settings_cache[setting.key] = setting.value
                    
            self._loaded = True
            logger.info(f"Loaded {len(self._settings_cache)} settings from database")
            
        except Exception as e:
            logger.error(f"Failed to load settings from database: {e}")
            
        finally:
            if close_db:
                await db.close()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key"""
        if not self._loaded:
            logger.warning(f"Settings not loaded, returning default for {key}")
            return default
        return self._settings_cache.get(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean setting"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer setting"""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_str(self, key: str, default: str = "") -> str:
        """Get a string setting"""
        value = self.get(key, default)
        return str(value) if value is not None else default
    
    async def refresh(self, db: Optional[AsyncSession] = None):
        """Refresh settings from database"""
        await self.load_settings(db)
    
    # LDAP-specific getters for convenience
    @property
    def LDAP_ENABLED(self) -> bool:
        return self.get_bool("ldap_enabled", False)
    
    @property
    def LDAP_SERVER(self) -> str:
        return self.get_str("ldap_server", "")
    
    @property
    def LDAP_PORT(self) -> int:
        return self.get_int("ldap_port", 389)
    
    @property
    def LDAP_USE_SSL(self) -> bool:
        return self.get_bool("ldap_use_ssl", False)
    
    @property
    def LDAP_START_TLS(self) -> bool:
        return self.get_bool("ldap_start_tls", False)
    
    @property
    def LDAP_BIND_DN(self) -> Optional[str]:
        return self.get_str("ldap_bind_dn") or None
    
    @property
    def LDAP_BIND_PASSWORD(self) -> Optional[str]:
        return self.get_str("ldap_bind_password") or None
    
    @property
    def LDAP_BASE_DN(self) -> str:
        return self.get_str("ldap_base_dn", "")
    
    @property
    def LDAP_USER_DN_TEMPLATE(self) -> str:
        return self.get_str("ldap_user_dn_template", "")
    
    @property
    def LDAP_USER_SEARCH_BASE(self) -> str:
        return self.get_str("ldap_user_search_base", "")
    
    @property
    def LDAP_USER_FILTER(self) -> str:
        return self.get_str("ldap_user_filter", "(objectClass=inetOrgPerson)")
    
    @property
    def LDAP_USER_ATTR_EMAIL(self) -> str:
        return self.get_str("ldap_user_attr_email", "mail")
    
    @property
    def LDAP_USER_ATTR_NAME(self) -> str:
        return self.get_str("ldap_user_attr_name", "displayName")
    
    @property
    def LDAP_USER_ATTR_UID(self) -> str:
        return self.get_str("ldap_user_attr_uid", "uid")
    
    @property
    def LDAP_AUTO_CREATE_USER(self) -> bool:
        return self.get_bool("ldap_auto_create_user", False)
    
    @property
    def LDAP_CONNECTION_TIMEOUT(self) -> int:
        return self.get_int("ldap_connection_timeout", 5)
    
    # Other settings that were hardcoded
    @property
    def ENABLE_RATE_LIMITING(self) -> bool:
        return self.get_bool("enable_rate_limiting", True)
    
    @property
    def RATE_LIMIT_PER_MINUTE(self) -> int:
        return self.get_int("rate_limit_per_minute", 60)
    
    @property
    def RATE_LIMIT_PER_HOUR(self) -> int:
        return self.get_int("rate_limit_per_hour", 600)
    
    @property
    def RATE_LIMIT_BURST(self) -> int:
        return self.get_int("rate_limit_burst", 10)
    
    @property
    def ENABLE_REQUEST_VALIDATION(self) -> bool:
        return self.get_bool("enable_request_validation", True)
    
    @property
    def ENABLE_SECURITY_HEADERS(self) -> bool:
        return self.get_bool("enable_security_headers", True)
    
    @property
    def ENABLE_AUDIT_LOGGING(self) -> bool:
        return self.get_bool("enable_audit_logging", True)
    
    @property
    def ADMIN_IP_WHITELIST(self) -> Optional[str]:
        return self.get_str("admin_ip_whitelist") or None
    
    # AI-specific settings
    @property
    def GROQ_API_KEY(self) -> str:
        return self.get_str("groq_api_key", "")
    
    @property
    def GROQ_MODEL(self) -> str:
        return self.get_str("groq_model", "llama-3.1-8b-instant")
    
    @property
    def AI_TEMPERATURE(self) -> float:
        value = self.get("ai_temperature", 0.3)
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.3
    
    @property
    def AI_MAX_TOKENS(self) -> int:
        return self.get_int("ai_max_tokens", 500)
    
    @property
    def AI_CACHE_TTL(self) -> int:
        return self.get_int("ai_cache_ttl", 86400)
    
    @property
    def AI_DAILY_TOKEN_LIMIT(self) -> int:
        return self.get_int("ai_daily_token_limit", 20000)
    
    @property
    def AI_USER_MONTHLY_TOKEN_LIMIT(self) -> int:
        return self.get_int("ai_user_monthly_token_limit", 50000)
    
    @property
    def ENABLE_AI_DUPLICATE_DETECTION(self) -> bool:
        return self.get_bool("enable_ai_duplicate_detection", True)
    
    @property
    def ENABLE_VECTOR_SEARCH(self) -> bool:
        return self.get_bool("enable_vector_search", True)
    
    # New provider settings
    @property
    def HUGGINGFACE_API_TOKEN(self) -> str:
        return self.get_str("huggingface_api_token", "")
    
    @property
    def HUGGINGFACE_MODEL(self) -> str:
        return self.get_str("huggingface_model", "microsoft/Phi-3-mini-4k-instruct")
    
    @property
    def HUGGINGFACE_PROVIDER(self) -> str:
        return self.get_str("huggingface_provider", "auto")
    
    @property
    def GEMINI_API_KEY(self) -> str:
        return self.get_str("gemini_api_key", "")
    
    @property
    def GEMINI_MODEL(self) -> str:
        return self.get_str("gemini_model", "gemini-1.5-flash")
    
    @property
    def AI_PROVIDER_PRIORITY(self) -> str:
        return self.get_str("ai_provider_priority", "huggingface,gemini,groq")
    
    @property
    def AI_PROVIDER_MODE(self) -> str:
        return self.get_str("ai_provider_mode", "hybrid")
    
    # Qdrant settings
    @property
    def QDRANT_HOST(self) -> str:
        return self.get_str("qdrant_host", "localhost")
    
    @property
    def QDRANT_PORT(self) -> int:
        return self.get_int("qdrant_port", 6333)
    
    @property
    def QDRANT_API_KEY(self) -> str:
        return self.get_str("qdrant_api_key", "")
    
    @property
    def QDRANT_COLLECTION_NAME(self) -> str:
        return self.get_str("qdrant_collection_name", "smart_todo_tasks")
    
    @property
    def QDRANT_EMBEDDING_MODEL(self) -> str:
        return self.get_str("qdrant_embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
    
    # MinIO settings
    @property
    def MINIO_ENDPOINT(self) -> str:
        return self.get_str("minio_endpoint", "localhost:9000")
    
    @property
    def MINIO_ACCESS_KEY(self) -> str:
        return self.get_str("minio_access_key", "minioadmin")
    
    @property
    def MINIO_SECRET_KEY(self) -> str:
        return self.get_str("minio_secret_key", "minioadmin")
    
    @property
    def MINIO_SECURE(self) -> bool:
        return self.get_bool("minio_secure", False)
    
    @property
    def MINIO_BUCKET_NAME(self) -> str:
        return self.get_str("minio_bucket_name", "smart-todo")


# Global dynamic settings instance
dynamic_settings = DynamicSettings()