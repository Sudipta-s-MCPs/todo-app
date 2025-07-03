# Environment Variables Usage Report
**Created: 2025-07-02**

This report identifies all occurrences of `os.getenv()` and `os.environ` usage in the backend codebase and their current status.

## Summary

Most environment variables have been successfully migrated to the database settings system. However, several critical configuration items still rely on environment variables.

## Environment Variables Still in Use

### 1. **Core Configuration** (in `app/config.py`)
These are loaded via Pydantic Settings and are **STILL REQUIRED** from environment:

- `DATABASE_URL` - PostgreSQL connection string (critical)
- `REDIS_URL` - Redis connection string (critical)
- `SECRET_KEY` - JWT signing key (critical)
- `CORS_ORIGINS` - CORS allowed origins
- `API_V1_PREFIX` - API version prefix
- `PROJECT_NAME` - Application name
- `VERSION` - Application version
- `ENVIRONMENT` - Runtime environment (development/production)
- `FRONTEND_URL` - Frontend URL (used in email service)
- OAuth settings:
  - `OAUTH_ENABLED`
  - `OAUTH_GOOGLE_CLIENT_ID`
  - `OAUTH_GOOGLE_CLIENT_SECRET`
  - `OAUTH_GITHUB_CLIENT_ID`
  - `OAUTH_GITHUB_CLIENT_SECRET`
- `MFA_ISSUER_NAME` - MFA issuer name
- `SENTRY_DSN` - Sentry error tracking
- `LOG_LEVEL` - Logging level
- `DESCRIPTION` - Application description

### 2. **Settings Service Default Values** (`app/services/settings_service.py`)
Uses `os.getenv()` extensively but **ONLY FOR INITIAL DEFAULTS** when populating the database:
- All settings are initialized from environment variables as defaults
- After initialization, values come from database
- Environment variables are not used after initial setup

### 3. **System Info Endpoint** (`app/api/v1/system.py`)
- Line 106: `os.getenv("ENVIRONMENT", "production")` - Used for displaying current environment

### 4. **Vector Service** (`app/services/vector_service.py`)
Still uses environment variables directly:
- `QDRANT_HOST` (line 44)
- `QDRANT_PORT` (line 45)
- `QDRANT_API_KEY` (line 46)
- `QDRANT_COLLECTION_NAME` (line 47)
- `QDRANT_EMBEDDING_MODEL` (line 48)

### 5. **Storage Service** (`app/services/storage_service.py`)
Still uses environment variables directly:
- `MINIO_ENDPOINT` (line 28)
- `MINIO_ACCESS_KEY` (line 29)
- `MINIO_SECRET_KEY` (line 30)
- `MINIO_SECURE` (line 31)
- `MINIO_BUCKET_NAME` (line 32)

### 6. **Duplicate Detection AI Service** (`app/services/duplicate_detection_ai.py`)
Still uses environment variables directly:
- `ENABLE_AI_DUPLICATE_DETECTION` (line 30)
- `ENABLE_VECTOR_SEARCH` (line 31)

### 7. **MCP Server** (`mcp_server/server.py` and `mcp_server/auth.py`)
Uses environment variables for MCP client configuration:
- `TODO_API_KEY`
- `TODO_USER_ID`
- `TODO_DEVICE_ID`
- `TODO_API_ENDPOINT`
- `TODO_DEVICE_NAME`

### 8. **Database Cleanup Script** (`scripts/cleanup_test_data.py`)
- `DATABASE_URL` (line 24) - For direct database connection

## Successfully Migrated to Database

The following have been successfully migrated and are loaded from database via `dynamic_settings`:

✅ Security Settings:
- ENABLE_RATE_LIMITING, RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_HOUR, RATE_LIMIT_BURST
- ENABLE_REQUEST_VALIDATION, ENABLE_SECURITY_HEADERS, ENABLE_AUDIT_LOGGING
- ADMIN_IP_WHITELIST

✅ Feature Flags:
- MFA_ENABLED, API_KEYS_ENABLED, WEBSOCKETS_ENABLED

✅ User Limits:
- MAX_WORKSPACES_PER_USER, MAX_TASKS_PER_LIST, MAX_LISTS_PER_WORKSPACE
- MAX_API_KEYS_PER_USER, MAX_DEVICES_PER_USER

✅ AI Settings:
- GROQ_API_KEY, GROQ_MODEL, AI_DAILY_TOKEN_LIMIT
- ENABLE_AI_DUPLICATE_DETECTION, AI_TEMPERATURE, AI_MAX_TOKENS
- AI_CACHE_TTL, AI_USER_MONTHLY_TOKEN_LIMIT, ENABLE_VECTOR_SEARCH
- HUGGINGFACE_API_TOKEN, HUGGINGFACE_MODEL
- GEMINI_API_KEY, GEMINI_MODEL
- AI_PROVIDER_PRIORITY, AI_PROVIDER_MODE

✅ LDAP Settings:
- All LDAP_* settings are properly migrated

✅ Email/SMTP Settings:
- All SMTP settings are stored in database (category: "email")

## Recommendations

1. **Critical Infrastructure Settings** (DATABASE_URL, REDIS_URL, SECRET_KEY):
   - Should remain as environment variables
   - These are needed to bootstrap the application

2. **Vector Service** (Qdrant settings):
   - Should be migrated to use `dynamic_settings`
   - Already exist in database, just need to update the service

3. **Storage Service** (MinIO settings):
   - Should be migrated to use `dynamic_settings`
   - Already exist in database, just need to update the service

4. **Duplicate Detection AI**:
   - Should be migrated to use `dynamic_settings`
   - Already exist in database, just need to update the service

5. **MCP Server Settings**:
   - Should remain as environment variables
   - These are client-specific configuration

6. **Frontend URL**:
   - Consider adding to database settings for email service
   - Currently only used in email templates

## Migration Status

- ✅ Complete: 43 settings migrated to database
- ⚠️ Partial: 3 services still using environment variables directly
- ❌ Not Migrated: Core infrastructure settings (by design)