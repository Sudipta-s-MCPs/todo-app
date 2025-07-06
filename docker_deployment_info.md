# Smart-ToDo - Complete Docker Deployment Information

## Build Summary
- **Build Date**: 2025-07-06 11:39:03 UTC
- **Tag**: latest
- **Platforms**: linux/amd64,linux/arm64
- **Registry**: GitHub Container Registry (ghcr.io)

## Images Built

### Backend API
- **Image**: `ghcr.io/sudipta-s-mcps/smart-todo-backend:latest`
- **Port**: 8000
- **Purpose**: FastAPI backend with MCP integration

### Frontend PWA
- **Image**: `ghcr.io/sudipta-s-mcps/smart-todo-frontend:latest`
- **Port**: 80 (Nginx)
- **Purpose**: React PWA for users

### Admin Panel
- **Image**: `ghcr.io/sudipta-s-mcps/smart-todo-admin:latest`
- **Port**: 3000
- **Purpose**: Admin interface for system management

### MCP Server
- **Image**: `ghcr.io/sudipta-s-mcps/smart-todo-mcp:latest`
- **Port**: 5485
- **Purpose**: MCP server for Claude Desktop integration

## Pull All Images
```bash
docker pull ghcr.io/sudipta-s-mcps/smart-todo-backend:latest
docker pull ghcr.io/sudipta-s-mcps/smart-todo-frontend:latest
docker pull ghcr.io/sudipta-s-mcps/smart-todo-admin:latest
docker pull ghcr.io/sudipta-s-mcps/smart-todo-mcp:latest
```

## Complete Portainer Stack
```yaml
version: '3.8'
services:
  backend:
    image: ghcr.io/sudipta-s-mcps/smart-todo-backend:latest
    ports:
      - "5482:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://sd_todo_app_user:password@192.168.11.100:15432/sd_todo_app_db
      - REDIS_URL=redis://192.168.11.100:6379/0
      - SECRET_KEY=your_secret_key
    networks:
      - smart-todo-network
    
  frontend:
    image: ghcr.io/sudipta-s-mcps/smart-todo-frontend:latest
    ports:
      - "5484:80"
    environment:
      - VITE_API_URL=http://192.168.11.100:5482/api/v1
    networks:
      - smart-todo-network
    depends_on:
      - backend
    
  admin-panel:
    image: ghcr.io/sudipta-s-mcps/smart-todo-admin:latest
    ports:
      - "5483:3000"
    environment:
      - VITE_API_URL=http://192.168.11.100:5482/api/v1
    networks:
      - smart-todo-network
    depends_on:
      - backend
    
  mcp-server:
    image: ghcr.io/sudipta-s-mcps/smart-todo-mcp:latest
    ports:
      - "5485:5485"
    environment:
      - TODO_API_ENDPOINT=http://192.168.11.100:5482/api/v1
      - MCP_SERVER_NAME=TodoApp
      - MCP_SERVER_VERSION=1.0.0
    networks:
      - smart-todo-network
    depends_on:
      - backend

networks:
  smart-todo-network:
    driver: bridge
```

## Health Checks
```bash
# Backend API
curl http://192.168.11.100:5482/health

# Frontend PWA
curl http://192.168.11.100:5484/

# Admin Panel
curl http://192.168.11.100:5483/

# MCP Server
curl http://192.168.11.100:5485/mcp/
```

## Security Notes
- All images run as non-root user (uid: 1000)
- Multi-stage builds for minimal attack surface
- Only runtime dependencies included
- Health checks configured for monitoring
- External database and Redis for data persistence
