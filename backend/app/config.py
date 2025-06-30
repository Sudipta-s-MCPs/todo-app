"""
Application configuration using Pydantic Settings
Created: 2025-01-30 13:48:00 PST
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    # Database
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/dbname"
    )
    
    # Redis
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0"
    )
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-here")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    MCP_TOKEN_EXPIRE_HOURS: int = Field(default=24)
    
    # API Configuration
    API_V1_PREFIX: str = Field(default="/api/v1")
    API_BASE_URL: str = Field(default="http://localhost:8000")
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"])
    
    # MCP Configuration
    MCP_SERVER_NAME: str = Field(default="TodoApp")
    MCP_SERVER_VERSION: str = Field(default="1.0.0")
    
    # Admin Configuration
    ADMIN_EMAIL: str = Field(default="admin@example.com")
    ADMIN_PASSWORD: str = Field(default="admin123")
    
    # Testing
    TEST_API_KEY: Optional[str] = Field(default=None)
    
    # OAuth (Optional)
    OAUTH_GOOGLE_CLIENT_ID: Optional[str] = Field(default=None)
    OAUTH_GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None)
    OAUTH_GITHUB_CLIENT_ID: Optional[str] = Field(default=None)
    OAUTH_GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None)
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None)
    LOG_LEVEL: str = Field(default="INFO")
    
    # Application
    PROJECT_NAME: str = Field(default="Smart-ToDo")
    VERSION: str = Field(default="1.0.0")
    DESCRIPTION: str = Field(default="Advanced ToDo Application with MCP Support")
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Return synchronous database URL for Alembic"""
        return str(self.DATABASE_URL).replace("+asyncpg", "")


settings = Settings()