# Deployment Guide

**Created**: 2025-01-30 14:57:00 PST  
**Last Modified**: 2025-01-30 14:57:00 PST

## Overview

This guide covers deploying Smart-ToDo to Synology NAS via Portainer using Docker Compose.

## Prerequisites

- Synology NAS with Docker and Portainer installed
- PostgreSQL and Redis running on Synology NAS
- Domain name (optional, for external access)
- SSL certificate (recommended)

## Deployment Steps

### 1. Prepare Environment

Create a `.env.production` file with production settings:

```env
# Database - Synology NAS Configuration
DATABASE_URL=postgresql+asyncpg://sd_todo_app_user:YOUR_SECURE_PASSWORD@192.168.11.100:15432/sd_todo_app_db
REDIS_URL=redis://192.168.11.100:6379/0

# Security
SECRET_KEY=generate-a-very-long-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# API Configuration
API_BASE_URL=https://todo.yourdomain.com
CORS_ORIGINS=["https://todo.yourdomain.com"]

# Admin Configuration
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=secure-admin-password

# Docker Profiles (empty for production)
COMPOSE_PROFILES=
```

### 2. Build Docker Images

On your development machine:

```bash
# Build backend image
docker build -t smart-todo-backend:latest ./backend

# Build admin panel image
docker build -t smart-todo-admin:latest ./admin-panel

# Build test client image (optional)
docker build -t smart-todo-test:latest ./test-client
```

### 3. Push to Registry (Optional)

If using a Docker registry:

```bash
docker tag smart-todo-backend:latest your-registry/smart-todo-backend:latest
docker push your-registry/smart-todo-backend:latest

docker tag smart-todo-admin:latest your-registry/smart-todo-admin:latest
docker push your-registry/smart-todo-admin:latest
```

### 4. Deploy via Portainer

1. **Access Portainer** on your Synology NAS

2. **Create Stack**:
   - Go to Stacks → Add Stack
   - Name: `smart-todo`
   - Use the docker-compose.yml file

3. **Configure Environment**:
   - Upload your `.env.production` as `.env`
   - Or set environment variables in Portainer

4. **Adjust Compose File**:
   ```yaml
   version: '3.8'

   services:
     backend:
       image: smart-todo-backend:latest
       container_name: smart-todo-backend
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=${DATABASE_URL}
         - REDIS_URL=${REDIS_URL}
         - SECRET_KEY=${SECRET_KEY}
         # ... other env vars
       volumes:
         - ./data:/app/data
       networks:
         - smart-todo-network
       restart: unless-stopped

     admin-panel:
       image: smart-todo-admin:latest
       container_name: smart-todo-admin
       ports:
         - "3000:3000"
       environment:
         - REACT_APP_API_URL=${API_BASE_URL}
       networks:
         - smart-todo-network
       depends_on:
         - backend
       restart: unless-stopped

   networks:
     smart-todo-network:
       driver: bridge

   volumes:
     data:
   ```

5. **Deploy Stack**:
   - Click "Deploy the stack"
   - Wait for containers to start

### 5. Initial Setup

1. **Check Health**:
   ```bash
   curl http://nas-ip:8000/health
   ```

2. **Access Admin Panel**:
   - Navigate to `http://nas-ip:3000`
   - Login with admin credentials

3. **Verify Database**:
   - Check that tables are created
   - Admin user exists

### 6. Configure Reverse Proxy

For external access, configure Synology's reverse proxy:

1. **Control Panel → Application Portal → Reverse Proxy**

2. **Create Rule for API**:
   - Source: `https://todo.yourdomain.com/api`
   - Destination: `http://localhost:8000`

3. **Create Rule for Admin**:
   - Source: `https://todo.yourdomain.com`
   - Destination: `http://localhost:3000`

4. **Enable WebSocket** (for real-time features):
   - Edit reverse proxy rule
   - Enable WebSocket support

### 7. SSL Configuration

1. **Control Panel → Security → Certificate**
2. **Add Certificate** for your domain
3. **Configure** reverse proxy to use HTTPS

## Monitoring

### Health Checks

Add health checks to docker-compose.yml:

```yaml
backend:
  healthcheck:
    test: ["CMD", "python", "scripts/health_check.py"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Logs

View logs in Portainer or via SSH:

```bash
docker logs smart-todo-backend
docker logs smart-todo-admin
```

### Metrics

Configure Synology's Resource Monitor to track:
- CPU usage
- Memory usage
- Network traffic
- Disk I/O

## Backup

### Database Backup

Create backup script on Synology:

```bash
#!/bin/bash
# backup_todo.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/volume1/backups/smart-todo"

# Backup PostgreSQL
docker exec synology-postgres pg_dump \
  -U sd_todo_app_user \
  -d sd_todo_app_db \
  > "$BACKUP_DIR/db_backup_$DATE.sql"

# Compress
gzip "$BACKUP_DIR/db_backup_$DATE.sql"

# Keep only last 7 days
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete
```

### Schedule Backups

Use Synology Task Scheduler:
1. Control Panel → Task Scheduler
2. Create → Scheduled Task → User-defined script
3. Schedule daily at 2 AM
4. Run backup script

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker logs smart-todo-backend
```

Common issues:
- Database connection failed
- Port already in use
- Environment variables missing

### Database Connection Issues

Test connection:
```bash
docker exec smart-todo-backend python -c "
from app.database import engine
import asyncio
asyncio.run(engine.connect())
"
```

### Performance Issues

1. Check container resources in Portainer
2. Increase memory limits if needed
3. Optimize PostgreSQL settings
4. Enable Redis persistence

## Security Hardening

1. **Change Default Passwords**
2. **Restrict Network Access**:
   - Use Synology firewall
   - Limit container networks
3. **Regular Updates**:
   - Update Docker images
   - Apply security patches
4. **Enable Fail2Ban** for brute force protection
5. **Regular Backups** with encryption