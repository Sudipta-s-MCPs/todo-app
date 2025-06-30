# Advanced ToDo App - Complete Implementation Plan

## Project Overview

A next-generation ToDo application with multi-device support, AI agent integration via MCP, comprehensive activity tracking, and a full-featured admin panel. The system will run on Synology NAS via Docker/Portainer, using PostgreSQL and Redis.

## Phase 1: Foundation Setup

### 1.1 Development Environment Setup

#### 1.1.1 Project Structure Creation
```
todo-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── api/
│   │   ├── services/
│   │   ├── middleware/
│   │   └── utils/
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── auth.py
│   │   ├── tools/
│   │   ├── resources/
│   │   └── prompts/
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── admin-panel/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

#### 1.1.2 Initial Dependencies Setup
- **Backend Requirements**:
  - FastAPI==0.104.1
  - uvicorn[standard]==0.24.0
  - sqlalchemy==2.0.23
  - asyncpg==0.29.0
  - redis==5.0.1
  - pydantic==2.5.0
  - pydantic-settings==2.1.0
  - python-jose[cryptography]==3.3.0
  - passlib[bcrypt]==1.7.4
  - python-multipart==0.0.6
  - httpx==0.25.2
  - fastmcp==2.0.0
  - alembic==1.13.0
  - celery==5.3.4
  - websockets==12.0

#### 1.1.3 Docker Configuration
- Create Dockerfile for backend with Python 3.11
- Create docker-compose.yml with services:
  - backend (FastAPI app)
  - admin-panel (React app)
  - NOTE: PostgreSQL and Redis are external services on Synology NAS
- Configure volumes for data persistence
- Set up environment variables
- Ensure network connectivity to Synology NAS services

### 1.2 Database Schema Implementation

#### 1.2.1 Core User Tables
- **users** table:
  - id (UUID primary key)
  - email (unique, indexed)
  - name
  - password_hash
  - avatar_url
  - settings_json (JSONB)
  - created_at, updated_at, last_active_at
  - timezone, locale

- **user_devices** table:
  - id (UUID primary key)
  - user_id (foreign key)
  - device_name
  - device_type (enum: web, mobile_ios, mobile_android, desktop, api, mcp_agent, other)
  - device_identifier (unique per user)
  - platform_details (JSONB)
  - last_ip_address, last_location
  - is_trusted, is_active
  - created_at, last_used_at

#### 1.2.2 Authentication Tables
- **api_keys** table:
  - id, user_id, key_hash (unique)
  - name, permissions (JSONB)
  - rate_limit, expires_at
  - last_used_at, created_at, is_active

- **mcp_agents** table:
  - id, user_id, agent_name
  - agent_identifier (unique)
  - capabilities, permissions (JSONB)
  - last_heartbeat, created_at, is_active

- **user_sessions** table:
  - id, user_id, device_id
  - session_token (unique)
  - ip_address, user_agent
  - access_method (enum)
  - created_at, expires_at, last_activity_at, is_active

#### 1.2.3 Workspace & Task Tables
- **workspaces** table:
  - id, name, type (personal/team/org)
  - owner_id, settings_json, created_at

- **workspace_members** table:
  - workspace_id, user_id, role
  - permissions_json, joined_at, invited_by

- **lists** table:
  - id, workspace_id, name, color, icon
  - type, position, settings_json, created_at

- **tasks** table with full attribution:
  - Basic fields: id, list_id, title, description, status, priority
  - Tracking fields: created_by, created_via_device_id, created_via_method, created_via_session_id
  - Task fields: due_date, completed_at, assigned_to[], parent_task_id
  - Metadata: position, metadata (JSONB), created_at, updated_at

#### 1.2.4 Tracking Tables
- **activity_log** table:
  - Comprehensive logging with user_id, action_type, resource_type/id
  - Full attribution: device_id, session_id, access_method, api_key_id, mcp_agent_id
  - Context: ip_address, user_agent, request_id

- **task_modifications** table:
  - Detailed change tracking per field
  - Attribution for each modification

### 1.3 Base Configuration

#### 1.3.1 Environment Configuration
- Create .env.example with all required variables:
  ```
  DATABASE_URL=postgresql://sd_todo_app_user:AAqLX5r0lzm53hgQu48XIClw@192.168.11.100:15432/sd_todo_app_db
  REDIS_URL=redis://192.168.11.100:6379/0
  SECRET_KEY=your-secret-key-here
  ALGORITHM=HS256
  ACCESS_TOKEN_EXPIRE_MINUTES=30
  REFRESH_TOKEN_EXPIRE_DAYS=7
  API_BASE_URL=http://localhost:8000
  CORS_ORIGINS=["http://localhost:3000"]
  ```

#### 1.3.2 Database Connection Setup
- Configure async SQLAlchemy with connection pooling
- Set up Redis connection with retry logic
- Create database initialization scripts
- Implement health check endpoints

## Phase 2: Core Authentication System

### 2.1 User Authentication

#### 2.1.1 Password Authentication
- Implement password hashing with bcrypt
- Create registration endpoint with email validation
- Create login endpoint with device tracking
- Implement password reset flow

#### 2.1.2 JWT Token Management
- Generate access and refresh tokens with device info
- Implement token refresh endpoint
- Create token blacklist in Redis
- Add token validation middleware

#### 2.1.3 OAuth 2.0 Implementation
- Set up OAuth providers (Google, GitHub)
- Create OAuth callback handlers
- Link OAuth accounts to existing users
- Handle OAuth state securely

### 2.2 Device & Session Management

#### 2.2.1 Device Registration
- Auto-detect device type from user agent
- Generate unique device identifiers
- Store device metadata and capabilities
- Implement device trust mechanism

#### 2.2.2 Session Creation
- Create sessions with device attribution
- Implement concurrent session limits
- Add session activity tracking
- Create session termination endpoints

#### 2.2.3 Multi-Factor Authentication
- Implement TOTP-based 2FA
- Create QR code generation for authenticator apps
- Add backup codes generation
- Implement 2FA enforcement policies

### 2.3 API Key Management

#### 2.3.1 API Key Generation
- Create secure key generation (32-byte tokens)
- Implement key hashing before storage
- Add key prefix for easy identification
- Generate different key types (read-only, read-write, admin)

#### 2.3.2 API Key Authentication
- Create API key authentication middleware
- Implement rate limiting per key
- Add key usage tracking
- Create key rotation endpoints

## Phase 3: Core Task Management

### 3.1 Workspace Implementation

#### 3.1.1 Workspace CRUD
- Create workspace creation endpoint
- Implement workspace types (personal, team, org)
- Add workspace settings management
- Create workspace deletion with cascade

#### 3.1.2 Workspace Membership
- Implement invitation system
- Create role-based permissions (owner, admin, member, viewer)
- Add bulk member operations
- Implement leave/remove member endpoints

### 3.2 List Management

#### 3.2.1 List Operations
- Create list CRUD endpoints
- Implement list ordering/positioning
- Add list color and icon customization
- Create list archiving functionality

#### 3.2.2 List Permissions
- Implement list-level access control
- Add list sharing capabilities
- Create public/private list toggles
- Implement list templates

### 3.3 Task Management

#### 3.3.1 Task CRUD with Attribution
- Create task with full device/method attribution
- Implement task update tracking
- Add bulk task operations
- Create task archiving/soft delete

#### 3.3.2 Duplicate Detection
- Implement similarity algorithm (title + description)
- Create duplicate checking endpoint
- Add user decision handling (update/create anyway/cancel)
- Store duplicate resolution history

#### 3.3.3 Task Features
- Implement subtasks/parent tasks
- Add task dependencies
- Create recurring tasks
- Implement task templates

#### 3.3.4 Task Assignment & Collaboration
- Implement multi-user assignment
- Add task comments with mentions
- Create task activity feed
- Implement real-time updates via WebSocket

## Phase 4: MCP Server Implementation

### 4.1 MCP Authentication System

#### 4.1.1 MCP-Specific API Keys
- Create MCP API key generation endpoint
- Add MCP-specific permissions model
- Implement higher rate limits for MCP
- Create key configuration export

#### 4.1.2 MCP Client Registration
- Create MCP agent registration system
- Implement capability declaration
- Add heartbeat mechanism
- Create agent deactivation flow

### 4.2 FastMCP Server Setup

#### 4.2.1 Server Initialization
- Set up FastMCP server with lifespan management
- Implement authentication on startup
- Create session management
- Add automatic token refresh

#### 4.2.2 Environment Configuration
- Define MCP environment variables:
  ```
  TODO_API_KEY=mcp_key_xxx
  TODO_USER_ID=user-uuid
  TODO_DEVICE_ID=mcp-agent-identifier
  TODO_API_ENDPOINT=http://localhost:8000/api/v1
  TODO_DEVICE_NAME=Agent Name
  ```

### 4.3 MCP Tools Implementation

#### 4.3.1 Task Management Tools
- **create_task**: Create tasks with natural language
- **list_tasks**: Query tasks with filters
- **update_task**: Modify task properties
- **complete_task**: Mark tasks as done
- **delete_task**: Remove tasks

#### 4.3.2 List Management Tools
- **create_list**: Create new lists
- **get_lists**: Retrieve user's lists
- **move_task**: Move tasks between lists

#### 4.3.3 Search Tools
- **search_tasks**: Full-text search
- **get_task_by_id**: Retrieve specific task
- **get_upcoming_tasks**: Get tasks by due date

### 4.4 MCP Resources

#### 4.4.1 Task Resources
- **tasks://recent**: Recently modified tasks
- **tasks://upcoming**: Tasks due soon
- **tasks://workspace/{id}**: Tasks in specific workspace

#### 4.4.2 List Resources
- **lists://all**: All user's lists
- **lists://shared**: Shared lists

### 4.5 MCP Prompts

#### 4.5.1 Task Creation Prompts
- Daily planning prompt
- Project breakdown prompt
- Meeting notes to tasks prompt

## Phase 5: Activity Tracking & Analytics

### 5.1 Activity Logging

#### 5.1.1 Comprehensive Logging
- Log all CRUD operations
- Track authentication events
- Record permission changes
- Monitor API usage

#### 5.1.2 Attribution Tracking
- Store device information for each action
- Track access method (web, api, mcp)
- Record session context
- Add request correlation IDs

### 5.2 Analytics Implementation

#### 5.2.1 User Analytics
- Device usage patterns
- Activity heatmaps
- Task completion rates
- Collaboration metrics

#### 5.2.2 System Analytics
- API endpoint usage
- Response time metrics
- Error rate tracking
- Rate limit statistics

## Phase 6: Real-time Features

### 6.1 WebSocket Implementation

#### 6.1.1 WebSocket Server
- Set up WebSocket endpoint
- Implement connection authentication
- Create room-based subscriptions
- Add connection pooling

#### 6.1.2 Real-time Events
- Task updates
- List changes
- User presence
- Collaboration notifications

### 6.2 Notification System

#### 6.2.1 In-app Notifications
- Create notification models
- Implement notification delivery
- Add read/unread tracking
- Create notification preferences

#### 6.2.2 Push Notifications
- Set up push notification service
- Implement device token management
- Create notification templates
- Add notification scheduling

## Phase 7: Admin Panel Implementation

### 7.1 Admin Authentication

#### 7.1.1 Admin User System
- Create admin user model
- Implement admin roles (super_admin, admin, support, viewer)
- Add admin-specific authentication
- Create admin session management

#### 7.1.2 Admin Security
- Implement IP allowlisting
- Enforce MFA for admins
- Add admin action audit logs
- Create permission matrix

### 7.2 User Management Interface

#### 7.2.1 User Dashboard
- User list with advanced search
- User detail views
- Activity timeline
- Device management interface

#### 7.2.2 User Operations
- Create/edit users
- Reset passwords
- Manage permissions
- Bulk operations

### 7.3 MCP Client Management

#### 7.3.1 Client Onboarding Wizard
- Step-by-step client setup
- Configuration generator
- Test connectivity tools
- Documentation integration

#### 7.3.2 Client Registry
- List all MCP clients
- Show online/offline status
- Display last activity
- Provide quick actions

### 7.4 Token Management Center

#### 7.4.1 Token Dashboard
- Visual token overview
- Usage statistics
- Expiration tracking
- Security alerts

#### 7.4.2 Token Operations
- Create tokens with templates
- Bulk token generation
- Token rotation scheduling
- Revocation with audit trail

### 7.5 System Administration

#### 7.5.1 System Monitoring
- Real-time metrics dashboard
- Error log viewer
- Performance analytics
- Resource utilization

#### 7.5.2 Configuration Management
- System settings interface
- Rate limit configuration
- Security policy management
- Backup/restore operations

## Phase 8: Testing & Security

### 8.1 Testing Implementation

#### 8.1.1 Unit Tests
- Model tests
- Service layer tests
- Utility function tests
- Authentication tests

#### 8.1.2 Integration Tests
- API endpoint tests
- Database operation tests
- MCP server tests
- WebSocket tests

#### 8.1.3 End-to-End Tests
- User journey tests
- Multi-device scenarios
- MCP client integration tests
- Admin panel workflows

### 8.2 Security Hardening

#### 8.2.1 Security Measures
- Input validation on all endpoints
- SQL injection prevention
- XSS protection
- CSRF token implementation

#### 8.2.2 Performance Security
- Rate limiting per user/device
- DDoS protection
- Request size limits
- Timeout configurations

## Phase 9: Deployment & Documentation

### 9.1 Deployment Setup

#### 9.1.1 Production Configuration
- Environment-specific settings
- Production database setup
- Redis cluster configuration
- SSL/TLS setup

#### 9.1.2 Docker Deployment
- Multi-stage Dockerfile optimization
- Docker Compose for production
- Volume management
- Network configuration

#### 9.1.3 Monitoring Setup
- Log aggregation
- Metric collection
- Alert configuration
- Backup automation

### 9.2 Documentation

#### 9.2.1 API Documentation
- OpenAPI/Swagger setup
- Endpoint descriptions
- Example requests/responses
- Error code reference

#### 9.2.2 MCP Documentation
- Client setup guides
- Tool/resource reference
- Example configurations
- Troubleshooting guide

#### 9.2.3 Admin Documentation
- Admin panel user guide
- Security best practices
- Operational procedures
- Disaster recovery plan

## Implementation Order & Dependencies

### Critical Path:
1. **Foundation** (Database, Basic Auth) → Must complete first
2. **Core Task Management** → Depends on Foundation
3. **MCP Server** → Depends on Auth & Task Management
4. **Admin Panel** → Can start after Core Task Management
5. **Real-time Features** → Can be added incrementally
6. **Testing & Security** → Continuous throughout
7. **Deployment** → Final phase

### Parallel Work Streams:
- Admin Panel frontend can be developed alongside backend
- MCP server can be prototyped early with mock data
- Testing infrastructure can be set up from Day 1

## Success Criteria

### Technical Requirements:
- ✓ All API endpoints return < 100ms (95th percentile)
- ✓ 99.9% uptime
- ✓ Zero critical security vulnerabilities
- ✓ Full test coverage (>80%)
- ✓ Complete API documentation

### Functional Requirements:
- ✓ Multi-device support with attribution
- ✓ MCP integration with authentication
- ✓ Duplicate detection accuracy >95%
- ✓ Real-time sync <500ms latency
- ✓ Admin panel with all planned features

### Deployment Requirements:
- ✓ Runs on Synology NAS via Docker
- ✓ Uses existing PostgreSQL and Redis
- ✓ Accessible via FastAPI and MCP
- ✓ Scalable to 1000+ concurrent users

## Notes for Claude Code Implementation

1. **Start with the Foundation**: Create the complete project structure first
2. **Use Type Hints**: Every function should have proper type annotations
3. **Implement Logging**: Add detailed logging from the beginning
4. **Error Handling**: Every endpoint needs proper error handling
5. **Testing**: Write tests as you implement features
6. **Documentation**: Document code as you write it
7. **Security First**: Implement security measures from the start
8. **Performance**: Use async/await properly, implement caching early
9. **Configuration**: Use pydantic settings for all configuration
10. **Database**: Use Alembic migrations from the beginning

## Environment Variables Template

```env
# Database - Synology NAS Configuration
DATABASE_URL=postgresql+asyncpg://sd_todo_app_user:XXXXXXXX@192.168.11.100:15432/sd_todo_app_db
REDIS_URL=redis://192.168.11.100:6379/0

# Security
SECRET_KEY=your-very-long-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
MCP_TOKEN_EXPIRE_HOURS=24

# API Configuration
API_V1_PREFIX=/api/v1
API_BASE_URL=http://localhost:8000
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# MCP Configuration
MCP_SERVER_NAME=TodoApp
MCP_SERVER_VERSION=1.0.0

# Admin Configuration
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-password

# External Services (if needed)
OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=
OAUTH_GITHUB_CLIENT_ID=
OAUTH_GITHUB_CLIENT_SECRET=

# Monitoring
SENTRY_DSN=
LOG_LEVEL=INFO
```

This plan provides a complete roadmap for implementing the advanced ToDo application with all requested features. Each section is broken down into specific, actionable tasks that Claude Code can execute sequentially.
