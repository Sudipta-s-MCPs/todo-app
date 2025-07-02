# Smart-ToDo Application

**Created**: 2025-01-30 13:45:00 PST  
**Last Modified**: 2025-01-30 15:10:00 PST  
**Version**: 1.0.0

## Overview

Smart-ToDo is an advanced task management application with multi-device support, AI agent integration via MCP (Model Context Protocol), comprehensive activity tracking, and a full-featured admin panel. The system runs on Synology NAS via Docker/Portainer.

### 🚀 Key Features

- **🔐 Multi-Device Support**: Track which device and method created/modified each task
- **🤖 AI Agent Integration**: Full MCP protocol support for AI assistants with task management tools
- **🔍 Smart Duplicate Detection**: Prevent duplicate tasks using similarity algorithms (80% threshold)
- **📊 Admin Panel**: React-based admin interface for user, MCP agent, and system management
- **🔄 Real-time Updates**: WebSocket support for live collaboration and notifications
- **🏷️ Flexible Organization**: Workspaces, lists, tags, and task assignments
- **📱 API-First Design**: RESTful API with OpenAPI documentation and multiple auth methods
- **🐳 Production-Ready**: Fully containerized with health checks and monitoring support

## Documentation Index

All project documentation is organized in the `/docs` folder:

- [API Documentation](docs/api.md) - REST API endpoints and usage
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
- MCP integration powered by FastMCP
- Deployed on Synology NAS infrastructure

---

For detailed documentation, please refer to the `/docs` folder or visit the API documentation at `/docs` when running locally.