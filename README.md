# Smart-ToDo - Production Ready Task Management System

Advanced ToDo Application with MCP (Model Context Protocol) integration for Claude Desktop.

## 🚀 Features

- **Full-Featured Task Management**: Workspaces, lists, tasks with priorities, due dates, and attachments
- **Claude Desktop Integration**: Native MCP server for seamless AI task management
- **Progressive Web App**: Mobile-first React frontend with offline capabilities
- **Admin Panel**: Comprehensive system administration interface
- **Multi-Architecture Support**: Docker images for AMD64 and ARM64
- **Production Ready**: External database/Redis, health monitoring, proper logging

## 🏗️ Architecture

### Services
- **Backend API**: FastAPI with SQLAlchemy, Redis caching, JWT authentication
- **Frontend PWA**: React TypeScript with Material-UI, service worker
- **Admin Panel**: React administration interface
- **MCP Server**: Claude Desktop integration server

### External Dependencies
- **PostgreSQL**: Primary database (running on Synology NAS)
- **Redis**: Caching and session storage (running on Synology NAS)

## 🐋 Docker Deployment

### Quick Deploy with Portainer

1. **Use the provided Portainer stack**:
   ```bash
   # Copy portainer-stack.yml to your Portainer stacks
   # Update IP addresses and environment variables as needed
   ```

2. **Deploy the stack** in Portainer on your Synology NAS

### Manual Docker Deployment

```bash
# Pull all images
docker pull ghcr.io/sudipta-s-mcps/smart-todo-backend:latest
docker pull ghcr.io/sudipta-s-mcps/smart-todo-frontend:latest
docker pull ghcr.io/sudipta-s-mcps/smart-todo-admin:latest
docker pull ghcr.io/sudipta-s-mcps/smart-todo-mcp:latest

# Deploy using docker-compose or the provided stack
```

## 🔧 Building from Source

### Prerequisites
- Docker with buildx support
- GitHub Personal Access Token with package write permissions

### Environment Setup
```bash
export GITHUB_USERNAME=your_github_username
export GITHUB_PAT=your_personal_access_token
```

### Build All Services
```bash
# Build and push all services
./build_and_push.sh --all v1.0.0

# Build individual services
./build_and_push.sh backend v1.0.0
./build_and_push.sh frontend v1.0.0
./build_and_push.sh admin v1.0.0
./build_and_push.sh mcp v1.0.0
```

## 🌐 Access Points

After deployment on Synology NAS (IP: 192.168.11.100):

- **Frontend PWA**: http://192.168.11.100:5484
- **Admin Panel**: http://192.168.11.100:5483
- **Backend API**: http://192.168.11.100:5482
- **MCP Server**: http://192.168.11.100:5485

## 🤖 Claude Desktop Integration

### Setup MCP Integration

1. **Configure Claude Desktop** with the MCP server endpoint:
   ```json
   {
     "mcpServers": {
       "todo-app": {
         "command": "stdio",
         "args": ["python", "/path/to/mcp_stdio_bridge.py"]
       }
     }
   }
   ```

2. **Available MCP Tools**:
   - `list_tasks` - Retrieve tasks with filtering
   - `get_lists` - Fetch all lists by workspace
   - `create_list` - Create new lists
   - `create_task` - Create new tasks
   - `update_task` - Update task properties
   - `complete_task` - Mark tasks as completed
   - `search_tasks` - Search tasks by text
   - `move_task` - Move tasks between lists
   - `get_upcoming_tasks` - Get tasks with due dates
   - `delete_task` - Archive/delete tasks

## 🏥 Health Monitoring

### Health Check Endpoints
```bash
# Backend API health
curl http://192.168.11.100:5482/health

# Frontend availability
curl http://192.168.11.100:5484/

# Admin panel availability
curl http://192.168.11.100:5483/

# MCP server health
curl http://192.168.11.100:5485/mcp/
```

### System Monitoring
- **Redis Status**: `/api/v1/system/redis-status` (admin only)
- **Services Status**: `/api/v1/system/services-status` (admin only)
- **System Info**: `/api/v1/system/info` (admin only)

## ⚙️ Configuration

### Environment Variables

Key production configuration in `portainer-stack.yml`:

```yaml
environment:
  - ENVIRONMENT=production
  - DATABASE_URL=postgresql+asyncpg://user:pass@192.168.11.100:15432/db
  - REDIS_URL=redis://192.168.11.100:6379/0
  - SECRET_KEY=your_secret_key
  - API_BASE_URL=http://192.168.11.100:5482
  - CORS_ORIGINS=["http://192.168.11.100:5483","http://192.168.11.100:5484"]
```

### Database Setup

Ensure PostgreSQL is running on your Synology NAS:
- **Host**: 192.168.11.100
- **Port**: 15432
- **Database**: sd_todo_app_db
- **User**: sd_todo_app_user

### Redis Setup

Ensure Redis is running on your Synology NAS:
- **Host**: 192.168.11.100
- **Port**: 6379
- **Database**: 0

## 🔒 Security Features

- **Non-root containers**: All images run as user ID 1000
- **JWT authentication**: Secure API access
- **Rate limiting**: Request throttling with Redis
- **CORS protection**: Configurable allowed origins
- **Health checks**: Automatic container monitoring
- **Input validation**: Comprehensive request validation

## 📊 Production Features

- **Activity Logging**: Comprehensive user action tracking
- **Device Management**: Multi-device session handling
- **Admin Panel**: User management, system monitoring
- **WebSocket Support**: Real-time updates
- **File Attachments**: Task file upload support
- **Duplicate Detection**: Smart task similarity checking
- **Caching**: Redis-based response caching

## 🔄 Updates

To update the deployment:

1. **Build new images**:
   ```bash
   ./build_and_push.sh --all v1.1.0
   ```

2. **Update Portainer stack** with new image tags

3. **Redeploy** the stack in Portainer

## 📚 Documentation

- **API Documentation**: Available at `/docs` endpoint
- **Admin Guide**: Access via admin panel
- **MCP Integration**: See Claude Desktop documentation

## 🛠️ Development

For local development:

```bash
# Start development environment
docker-compose up -d

# Backend will be available at http://localhost:5482
# Frontend at http://localhost:5484
# Admin panel at http://localhost:5483
# MCP server at http://localhost:5485
```

## 📝 License

This project is for personal use. All rights reserved.

---

**Built with ❤️ for Synology NAS deployment via Portainer**

## Overview

Smart-ToDo is an advanced task management application with multi-device support, AI agent integration via MCP (Model Context Protocol), comprehensive activity tracking, and a full-featured admin panel. The system runs on Synology NAS via Docker/Portainer.

### 🚀 Key Features

- **🔐 Multi-Device Support**: Track which device and method created/modified each task
- **🤖 AI Agent Integration**: Full MCP protocol support for AI assistants with task management tools
- **🧠 AI-Powered Features**: 
  - Semantic duplicate detection using remote LLMs (HuggingFace, Groq, Gemini)
  - Natural language task creation with smart parsing
  - Automatic workspace/list categorization
  - Intelligent task suggestions and merging
- **🔍 Smart Duplicate Detection**: AI-enhanced detection with semantic understanding + traditional similarity algorithms
- **📊 Admin Panel**: React-based admin interface for user, MCP agent, and system management
- **🔄 Real-time Updates**: WebSocket support for live collaboration and notifications
- **🏷️ Flexible Organization**: Workspaces, lists, tags, and task assignments
- **📱 API-First Design**: RESTful API with OpenAPI documentation and multiple auth methods
- **🐳 Production-Ready**: Fully containerized with health checks and monitoring support
- **💰 Cost-Effective AI**: Optimized to stay under $2/month even with 10+ active users
- **🪶 Lightweight Architecture**: No local ML models - all AI via remote APIs (perfect for NAS deployment)

## Documentation Index

All project documentation is organized in the `/docs` folder:

- [API Documentation](docs/api.md) - REST API endpoints and usage
- [AI Features Guide](docs/ai-features.md) - AI-powered capabilities and configuration
- [MCP Integration Guide](docs/mcp-integration.md) - MCP server setup and tools
- [Admin Panel Guide](docs/admin-panel.md) - Admin interface documentation
- [Deployment Guide](docs/deployment.md) - Docker and Synology NAS deployment
- [Development Guide](docs/development.md) - Local development setup
- [Testing Guide](docs/testing.md) - Production-level testing procedures

## Quick Start

### Prerequisites

- Docker Desktop installed on your Mac
- Access to Synology NAS with PostgreSQL and Redis
- Git for version control

### Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Smart-ToDo
   ```

2. Copy environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Start services (choose one):
   
   **For local development with local PostgreSQL/Redis:**
   ```bash
   ./deploy_local.sh
   ```
   
   **For production deployment (using NAS PostgreSQL/Redis):**
   ```bash
   ./deploy_production.sh
   ```

4. Access the services:
   - Backend API: http://localhost:5482
   - Admin Panel: http://localhost:5483
   - Frontend App: http://localhost:5484
   - API Documentation: http://localhost:5482/docs
   - MCP Server: ws://localhost:5485 (when running)

5. Default admin credentials:
   - Email: admin@example.com
   - Password: admin123

## Project Structure

```
Smart-ToDo/
├── backend/          # FastAPI backend application
├── frontend/         # React PWA for regular users
├── admin-panel/      # React admin interface
├── test-client/      # Production API testing client
├── docs/            # Project documentation
├── .claude/         # Claude-specific files and temp storage
└── docker-compose.yml # Single compose file for all environments
```

## Technology Stack

### Backend
- **Framework**: FastAPI with async SQLAlchemy
- **Database**: PostgreSQL 15+ with full-text search
- **Cache**: Redis for session management and caching
- **Authentication**: JWT tokens, API keys, MFA support (TOTP)
- **WebSocket**: Native FastAPI WebSocket support
- **Task Queue**: Celery (optional, for background tasks)

### Frontend
- **User App**: React 18 PWA with TypeScript
- **Admin Panel**: React 18 with TypeScript
- **UI Framework**: Material-UI v5
- **State Management**: Zustand
- **Data Fetching**: Axios with React Query
- **Build Tool**: Vite
- **PWA Support**: Vite PWA Plugin with Workbox

### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose (single file for all environments)
- **Deployment**: Synology NAS via Portainer
- **Monitoring**: Health checks, optional Prometheus metrics

## Architecture Highlights

### API Design
- RESTful API with OpenAPI/Swagger documentation
- Multiple authentication methods (JWT, API keys, MCP agents)
- Comprehensive error handling with detailed responses
- Rate limiting and request throttling
- CORS support for web clients

### Database Schema
- Normalized design with proper indexes
- Full activity tracking with device attribution
- Soft deletes for data recovery
- Optimistic locking for concurrent updates
- JSON fields for flexible metadata

### Security Features
- Password hashing with bcrypt
- JWT with refresh token rotation
- API key scoping and permissions
- Input validation and sanitization
- SQL injection protection via ORM
- XSS prevention in admin panel

## Development Guidelines

1. **Docker-First Development**: All development happens inside Docker containers
2. **Virtual Environments**: Project-specific environments are managed by Docker
3. **Production Testing**: No mock testing - only production-level testing with live APIs
4. **Documentation**: Document all changes with timestamps in appropriate files
5. **Version Control**: Use branches for experiments, main branch for stable code
6. **Cleanup Tracking**: Track temporary files in CLAUDE_CLEANUP.md

## Testing

### Standalone Test Runner (Recommended)
```bash
# Run tests against local deployment
./run_prod_tests.py

# Run tests against production (NAS)
./run_prod_tests.py --api-url http://192.168.11.100:5482

# Run with specific credentials
./run_prod_tests.py --api-url http://192.168.11.100:5482 --api-key your-api-key

# Include WebSocket tests
./run_prod_tests.py --websocket
```

### Docker-based Testing (Alternative)
```bash
# Run all tests in Docker
docker-compose --profile test run test-client

# Run specific test suite
docker-compose --profile test run test-client pytest test_api.py::TestAuthentication -v
```

## Deployment to Production

See [Deployment Guide](docs/deployment.md) for detailed instructions on deploying to Synology NAS.

## Monitoring and Maintenance

- **Health Checks**: `/health` endpoint for service monitoring
- **Logs**: Structured JSON logging with correlation IDs
- **Metrics**: Optional Prometheus metrics at `/metrics`
- **Backups**: Automated PostgreSQL backups via Synology Task Scheduler

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the development guidelines above
4. Commit your changes with descriptive messages
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

[Specify your license here]

## Acknowledgments

- Built with FastAPI and React
- MCP integration using official MCP library (Claude Desktop compatible)
- Deployed on Synology NAS infrastructure

---

For detailed documentation, please refer to the `/docs` folder or visit the API documentation at `/docs` when running locally.