# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart-ToDo is a production-ready task management system with MCP (Model Context Protocol) integration for Claude Desktop. The application consists of multiple Docker services running on a Synology NAS.

## Architecture

### Services Structure
- **backend/** - FastAPI application with SQLAlchemy ORM
- **frontend/** - React PWA with Material-UI
- **admin-panel/** - React admin interface 
- **mcp_server/** - MCP server for Claude Desktop integration
- **test-client/** - Production testing suite

### Database Schema
- PostgreSQL with async SQLAlchemy
- Models in `backend/app/models/`
- Alembic migrations in `backend/alembic/versions/`
- Activity tracking with device attribution

### Key Components
- **Authentication**: JWT tokens, API keys, MCP agent auth
- **WebSocket**: Real-time updates via FastAPI WebSocket
- **AI Integration**: Groq LLM for duplicate detection and smart parsing
- **Caching**: Redis for sessions and response caching
- **File Storage**: MinIO for task attachments

## Development Commands

### Frontend (React PWA)
```bash
cd frontend
npm run dev      # Development server
npm run build    # Production build
npm run lint     # ESLint
```

### Admin Panel (React)
```bash
cd admin-panel
npm run dev      # Development server
npm run build    # Production build
npm run lint     # ESLint
```

### Backend (FastAPI)
```bash
cd backend
# Run via Docker - no direct Python commands
```

### Testing
```bash
# Comprehensive production testing
./run_prod_tests.py

# Test against production NAS
./run_prod_tests.py --api-url http://192.168.11.100:5482

# Docker-based testing
./run_all_tests.sh
```

### Deployment
```bash
# Local development
./deploy_local.sh

# Production deployment
./deploy_production.sh

# Build and push images
./build_and_push.sh --all v1.0.0
```

## Key Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string  
- `SECRET_KEY`: JWT signing key
- `API_BASE_URL`: Backend API URL
- `CORS_ORIGINS`: Allowed frontend origins

### Database Connection
- Production: `postgresql+asyncpg://user:pass@192.168.11.100:15432/db`
- Uses async SQLAlchemy with connection pooling

### MCP Integration
- MCP server exposes task management tools to Claude Desktop
- Authentication via HTTP headers or request context
- Tools: list_tasks, create_task, update_task, search_tasks, etc.

## Development Workflow

1. **Docker-First**: All development happens in Docker containers
2. **Production Testing**: Use `run_prod_tests.py` for comprehensive testing
3. **Database Migrations**: Use Alembic for schema changes
4. **API Documentation**: Available at `/docs` endpoint
5. **Health Checks**: Monitor via `/health` endpoints

## Key Files

- `docker-compose.yml`: Multi-environment Docker configuration
- `portainer-stack.yml`: Production deployment stack
- `backend/app/main.py`: FastAPI application entry point
- `backend/app/models/`: Database models
- `backend/app/api/v1/`: API route definitions
- `frontend/src/services/api.ts`: Frontend API client
- `mcp_server/server.py`: MCP server implementation

## Production Deployment

System runs on Synology NAS (192.168.11.100) via Portainer:
- Frontend: Port 5484
- Admin Panel: Port 5483  
- Backend API: Port 5482
- MCP Server: Port 5485

External services:
- PostgreSQL: Port 15432
- Redis: Port 6379