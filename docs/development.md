# Development Guide

**Created**: 2025-01-30 14:58:00 PST  
**Last Modified**: 2025-01-30 14:58:00 PST

## Overview

This guide covers local development setup for Smart-ToDo using Docker Compose.

## Prerequisites

- Docker Desktop installed
- Git
- Code editor (VS Code recommended)
- Postman or similar API testing tool (optional)

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Smart-ToDo
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration if needed
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Check services**:
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Admin Panel: http://localhost:3000

## Development Workflow

### Backend Development

1. **Make changes** to Python files in `backend/`

2. **Auto-reload**: The backend container watches for changes and reloads automatically

3. **View logs**:
   ```bash
   docker-compose logs -f backend
   ```

4. **Run commands** inside container:
   ```bash
   docker-compose exec backend bash
   # Inside container:
   python scripts/init_db.py
   alembic revision -m "Add new column"
   ```

### Frontend Development

1. **Make changes** to React files in `admin-panel/src/`

2. **Hot reload**: Vite provides instant updates

3. **View logs**:
   ```bash
   docker-compose logs -f admin-panel
   ```

4. **Install packages**:
   ```bash
   docker-compose exec admin-panel npm install package-name
   ```

### Database Management

1. **Create migration**:
   ```bash
   docker-compose exec backend alembic revision --autogenerate -m "Description"
   ```

2. **Run migrations**:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

3. **Rollback migration**:
   ```bash
   docker-compose exec backend alembic downgrade -1
   ```

4. **Access database**:
   ```bash
   docker-compose exec postgres psql -U sd_todo_app_user -d sd_todo_app_db
   ```

## Testing

### Run API Tests

```bash
docker-compose --profile test run test-client
```

### Test Specific Endpoints

```bash
# Test authentication
docker-compose --profile test run test-client pytest test_api.py::TestAuthentication -v

# Test with coverage
docker-compose --profile test run test-client pytest --cov=. -v
```

### Test WebSocket Functionality

```bash
# Test WebSocket real-time updates
docker-compose --profile test run test-client python test_websocket.py
```

### Manual Testing

Use the API documentation at http://localhost:8000/docs for interactive testing.

## MCP Development

### Test MCP Server Locally

1. **Set up MCP environment**:
   ```bash
   export TODO_API_KEY=your-test-api-key
   export TODO_API_ENDPOINT=http://localhost:8000/api/v1
   ```

2. **Run MCP server**:
   ```bash
   docker-compose exec backend python mcp_server/server_official.py
   ```

3. **Test with client**:
   ```python
   # Using official MCP library
   from mcp.client import Client
   from mcp.client.stdio import stdio_client
   
   # Connect via stdio
   async with stdio_client() as (read_stream, write_stream):
       async with Client(read_stream, write_stream) as client:
           result = await client.call_tool("list_tasks", {})
       print(result)
   ```

## Code Quality

### Linting

```bash
# Python linting
docker-compose exec backend flake8 .

# TypeScript linting
docker-compose exec admin-panel npm run lint
```

### Type Checking

```bash
# Python type checking
docker-compose exec backend mypy .

# TypeScript checking
docker-compose exec admin-panel npm run build
```

### Code Formatting

```bash
# Format Python code
docker-compose exec backend black .

# Format TypeScript/React
docker-compose exec admin-panel npm run format
```

## Debugging

### Backend Debugging

1. **Add breakpoint**:
   ```python
   import debugpy
   debugpy.listen(5678)
   debugpy.wait_for_client()
   # Your code here
   ```

2. **Connect debugger** (VS Code):
   - Add launch configuration
   - Attach to port 5678

### Frontend Debugging

1. **Use browser DevTools**
2. **React Developer Tools extension**
3. **Add console.log or debugger statements**

### Database Debugging

1. **Enable SQL logging**:
   ```python
   # In backend/app/database.py
   engine = create_async_engine(
       str(settings.DATABASE_URL),
       echo=True  # Enable SQL logging
   )
   ```

2. **View query plans**:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM tasks WHERE ...;
   ```

## Common Issues

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Stop all containers
docker-compose down

# Restart
docker-compose up -d
```

### Database Connection Failed

1. Check if PostgreSQL is running:
   ```bash
   docker-compose ps
   ```

2. Verify connection string in `.env`

3. Check network connectivity:
   ```bash
   docker-compose exec backend ping postgres
   ```

### Package Installation Issues

Clear Docker caches:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Performance Optimization

### Backend

1. **Use async/await** properly
2. **Implement caching** with Redis
3. **Optimize database queries**:
   - Use eager loading
   - Add proper indexes
   - Avoid N+1 queries

### Frontend

1. **Code splitting** with React.lazy
2. **Memoization** with React.memo
3. **Virtual scrolling** for long lists
4. **Image optimization**

## Git Workflow

### Feature Development

1. **Create branch**:
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make changes** and test

3. **Commit**:
   ```bash
   git add .
   git commit -m "Add new feature"
   ```

4. **Push**:
   ```bash
   git push origin feature/new-feature
   ```

### Commit Guidelines

- Use clear, descriptive messages
- Reference issue numbers
- Keep commits focused

Example:
```
feat: Add bulk task operations

- Implement bulk delete endpoint
- Add UI for multi-select
- Update API documentation

Fixes #123
```

## VS Code Setup

Recommended extensions:
- Python
- Pylance
- ESLint
- Prettier
- Docker
- GitLens

Settings (.vscode/settings.json):
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "typescript.tsdk": "admin-panel/node_modules/typescript/lib"
}
```