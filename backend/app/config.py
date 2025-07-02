"""
Application configuration using Pydantic Settings
Created: 2025-01-30 13:48:00 PST
"""

from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
import json
import secrets
import warnings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields from .env
    )

    # Database
    DATABASE_URL: Optional[PostgresDsn] = Field(
        default=None,
        description="PostgreSQL database URL (required in production)"
    )
    
    # Redis
    REDIS_URL: Optional[RedisDsn] = Field(
        default=None,
        description="Redis server URL (required in production)"
    )
    
    # Security
    SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Secret key for JWT encoding (required in production)"
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    MCP_TOKEN_EXPIRE_HOURS: int = Field(default=24)
    
    # Security Features
    ENABLE_RATE_LIMITING: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_PER_HOUR: int = Field(default=600)
    RATE_LIMIT_BURST: int = Field(default=10)
    
    ENABLE_REQUEST_VALIDATION: bool = Field(default=True)
    ENABLE_SECURITY_HEADERS: bool = Field(default=True)
    ENABLE_AUDIT_LOGGING: bool = Field(default=True)
    
    # IP Whitelist for admin endpoints (optional)
    ADMIN_IP_WHITELIST: Optional[List[str]] = Field(default=None)
    
    # API Configuration
    API_V1_PREFIX: str = Field(default="/api/v1")
    API_BASE_URL: str = Field(default="http://localhost:8000")
    CORS_ORIGINS: Union[List[str], str] = Field(default=["http://localhost:3000"])
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                # Try to parse as JSON
                return json.loads(v)
            except json.JSONDecodeError:
                # If not JSON, split by comma
                return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator('ADMIN_IP_WHITELIST', mode='before')
    @classmethod
    def parse_ip_whitelist(cls, v):
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(',') if ip.strip()]
        return v
    
    @field_validator('ADMIN_USERS', mode='before')
    @classmethod
    def parse_admin_users(cls, v):
        if isinstance(v, str):
            return [user.strip() for user in v.split(',') if user.strip()]
        return v
    
    # MCP Configuration
    MCP_SERVER_NAME: str = Field(default="TodoApp")
    MCP_SERVER_VERSION: str = Field(default="1.0.0")
    
    # Admin Configuration
    ADMIN_USERS: Optional[List[str]] = Field(default=None)
    
    # OAuth (Optional)
    OAUTH_ENABLED: bool = Field(default=False)
    OAUTH_GOOGLE_CLIENT_ID: Optional[str] = Field(default=None)
    OAUTH_GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None)
    OAUTH_GITHUB_CLIENT_ID: Optional[str] = Field(default=None)
    OAUTH_GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None)
    
    # MFA Configuration
    MFA_ENABLED: bool = Field(default=True)
    MFA_ISSUER_NAME: str = Field(default="Smart-ToDo")
    
    # API Keys Configuration
    API_KEYS_ENABLED: bool = Field(default=True)
    MAX_API_KEYS_PER_USER: int = Field(default=5)
    
    # WebSocket Configuration  
    WEBSOCKETS_ENABLED: bool = Field(default=True)
    
    # LDAP Configuration
    LDAP_ENABLED: bool = Field(default=False)
    LDAP_SERVER: str = Field(default="sudipta.synology.me")
    LDAP_PORT: int = Field(default=389)
    LDAP_USE_SSL: bool = Field(default=False)
    LDAP_START_TLS: bool = Field(default=False)
    LDAP_BIND_DN: Optional[str] = Field(default=None)
    LDAP_BIND_PASSWORD: Optional[str] = Field(default=None)
    LDAP_BASE_DN: str = Field(default="dc=sudipta,dc=synology,dc=me")
    LDAP_USER_DN_TEMPLATE: str = Field(default="uid={username},cn=users,dc=sudipta,dc=synology,dc=me")
    LDAP_USER_SEARCH_BASE: str = Field(default="cn=users,dc=sudipta,dc=synology,dc=me")
    LDAP_USER_FILTER: str = Field(default="(objectClass=inetOrgPerson)")
    LDAP_USER_ATTR_EMAIL: str = Field(default="mail")
    LDAP_USER_ATTR_NAME: str = Field(default="displayName")
    LDAP_USER_ATTR_UID: str = Field(default="uid")
    LDAP_GROUP_SEARCH_BASE: str = Field(default="cn=groups,dc=sudipta,dc=synology,dc=me")
    LDAP_GROUP_FILTER: str = Field(default="(objectClass=groupOfNames)")
    LDAP_CONNECTION_TIMEOUT: int = Field(default=5)
    LDAP_AUTO_CREATE_USER: bool = Field(default=True)
    
    # User Limits
    MAX_WORKSPACES_PER_USER: int = Field(default=10)
    MAX_LISTS_PER_WORKSPACE: int = Field(default=50)
    MAX_TASKS_PER_LIST: int = Field(default=1000)
    MAX_DEVICES_PER_USER: int = Field(default=10)
    
    # AI Configuration
    GROQ_API_KEY: Optional[str] = Field(default=None)
    GROQ_MODEL: str = Field(default="llama-3.1-8b-instant")
    AI_DAILY_TOKEN_LIMIT: int = Field(default=20000)
    AI_USER_MONTHLY_TOKEN_LIMIT: int = Field(default=50000)
    AI_TEMPERATURE: float = Field(default=0.3)
    AI_MAX_TOKENS: int = Field(default=500)
    AI_CACHE_TTL: int = Field(default=86400)
    USER_MONTHLY_TOKEN_LIMIT: int = Field(default=50000)  # Alias for compatibility
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None)
    LOG_LEVEL: str = Field(default="INFO")
    
    # Application
    PROJECT_NAME: str = Field(default="Smart-ToDo")
    VERSION: str = Field(default="1.0.0")
    DESCRIPTION: str = Field(default="Advanced ToDo Application with MCP Support")
    ENVIRONMENT: str = Field(default="development")
    
    # Validators temporarily disabled for migration
    # TODO: Fix validators for Pydantic v2
    # @field_validator('SECRET_KEY', mode='after')
    # @classmethod
    # def validate_secret_key(cls, v, info):
    #     """Validate secret key is secure"""
    #     env = info.data.get('ENVIRONMENT', 'development') if hasattr(info, 'data') else 'development'
    #     if env == 'production' and (not v or v == 'your-secret-key-here' or len(v) < 32):
    #         raise ValueError(
    #             "SECRET_KEY must be set to a secure value in production. "
    #             "Use a cryptographically secure random string of at least 32 characters."
    #         )
    #     elif env == 'development' and (not v or v == 'your-secret-key-here'):
    #         # Generate a random key for development
    #         return secrets.token_urlsafe(32)
    #     return v
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set defaults for development
        if self.ENVIRONMENT == 'development':
            if not self.SECRET_KEY:
                self.SECRET_KEY = secrets.token_urlsafe(32)
            if not self.DATABASE_URL:
                self.DATABASE_URL = PostgresDsn("postgresql+asyncpg://postgres:postgres@localhost:5432/smart_todo")
            if not self.REDIS_URL:
                self.REDIS_URL = RedisDsn("redis://localhost:6379/0")
        
        # Show warnings for insecure configurations
        if self.ENVIRONMENT == 'production':
            if not self.SECRET_KEY or self.SECRET_KEY == 'your-secret-key-here':
                raise ValueError("SECRET_KEY must be set in production")
            
            if not self.DATABASE_URL:
                raise ValueError("DATABASE_URL must be set in production")
                
            if not self.REDIS_URL:
                raise ValueError("REDIS_URL must be set in production")
            
            if not self.ADMIN_USERS:
                warnings.warn(
                    "ADMIN_USERS not configured. No users will have admin access.",
                    UserWarning
                )
            
            if not self.OAUTH_ENABLED and not self.MFA_ENABLED:
                warnings.warn(
                    "Neither OAuth nor MFA is enabled. Consider enabling at least one for better security.",
                    UserWarning
                )
            
            if not self.ENABLE_RATE_LIMITING:
                warnings.warn(
                    "Rate limiting is disabled. This may expose the API to abuse.",
                    UserWarning
                )
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Return synchronous database URL for Alembic"""
        return str(self.DATABASE_URL).replace("+asyncpg", "")


settings = Settings()