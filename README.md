# Smart-ToDo Application

**Created**: 2025-01-30 13:45:00 PST  
**Last Modified**: 2025-01-30 13:45:00 PST

## Overview

Smart-ToDo is an advanced task management application with multi-device support, AI agent integration via MCP (Model Context Protocol), comprehensive activity tracking, and a full-featured admin panel. The system runs on Synology NAS via Docker/Portainer.

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

3. Start the application with Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Access the services:
   - Backend API: http://localhost:8000
   - Admin Panel: http://localhost:3000
   - API Documentation: http://localhost:8000/docs

## Project Structure

```
Smart-ToDo/
├── backend/          # FastAPI backend application
├── admin-panel/      # React admin interface
├── test-client/      # Production API testing client
├── docs/            # Project documentation
├── .claude/         # Claude-specific files and temp storage
└── docker-compose.yml # Single compose file for all environments
```

## Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL (on Synology NAS)
- **Cache**: Redis (on Synology NAS)
- **Admin Panel**: React with TypeScript
- **MCP Integration**: FastMCP for AI agent communication
- **Containerization**: Docker with Docker Compose

## Key Features

- Multi-device support with comprehensive tracking
- AI agent integration via MCP
- Duplicate task detection
- Real-time updates via WebSocket
- Comprehensive activity logging
- Full-featured admin panel
- Production-level API testing

## Development Guidelines

1. All development happens inside Docker containers
2. Use project-specific virtual environments (handled by Docker)
3. No mock testing - only production-level testing with live APIs
4. Document all changes with timestamps
5. Use branches for experiments
6. Track temporary files in CLAUDE_CLEANUP.md

## Support

For issues or questions, please refer to the documentation in the `/docs` folder or create an issue in the repository.