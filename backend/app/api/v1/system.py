"""
System information and health API endpoints
Created: 2025-01-30 18:57:00 PST
"""

import os
import psutil
import platform
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user, get_current_admin_user
from app.config import settings

router = APIRouter()


@router.get("/info", response_model=Dict[str, Any])
async def get_system_info(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system information (admin only)"""
    
    # System information
    system_info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "hostname": platform.node()
    }
    
    # CPU information
    cpu_info = {
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "cpu_usage_percent": psutil.cpu_percent(interval=1),
        "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
    }
    
    # Memory information
    memory = psutil.virtual_memory()
    memory_info = {
        "total": memory.total,
        "available": memory.available,
        "used": memory.used,
        "percent": memory.percent,
        "free": memory.free
    }
    
    # Disk information
    disk = psutil.disk_usage('/')
    disk_info = {
        "total": disk.total,
        "used": disk.used,
        "free": disk.free,
        "percent": disk.percent
    }
    
    # Database information
    try:
        # Get PostgreSQL version
        result = await db.execute(text("SELECT version()"))
        db_version = result.scalar()
        
        # Get database size
        db_name = settings.DATABASE_URL.path.lstrip('/')
        size_query = text(
            "SELECT pg_database_size(:db_name) as size"
        )
        size_result = await db.execute(size_query, {"db_name": db_name})
        db_size = size_result.scalar()
        
        # Get connection stats
        conn_query = text("""
            SELECT 
                count(*) as total_connections,
                count(*) filter (where state = 'active') as active_connections,
                count(*) filter (where state = 'idle') as idle_connections
            FROM pg_stat_activity
            WHERE datname = :db_name
        """)
        conn_result = await db.execute(conn_query, {"db_name": db_name})
        conn_stats = conn_result.fetchone()._asdict()
        
        database_info = {
            "version": db_version,
            "size": db_size,
            "connections": conn_stats
        }
    except Exception as e:
        database_info = {"error": str(e)}
    
    # Application information
    app_info = {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": os.getenv("ENVIRONMENT", "production"),
        "uptime": datetime.utcnow().isoformat(),
        "api_prefix": settings.API_V1_PREFIX,
        "debug_mode": False  # Should always be False in production
    }
    
    return {
        "system": system_info,
        "cpu": cpu_info,
        "memory": memory_info,
        "disk": disk_info,
        "database": database_info,
        "application": app_info
    }


@router.get("/health", response_model=Dict[str, Any])
async def get_system_health(
    db: AsyncSession = Depends(get_db)
):
    """Get system health status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database health check
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Redis health check
    try:
        # Import here to avoid circular imports
        from app.services.cache import redis_cache
        if await redis_cache.ping():
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "message": "Redis connection successful"
            }
        else:
            health_status["checks"]["redis"] = {
                "status": "unhealthy",
                "message": "Redis connection failed"
            }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
    
    # Memory health check
    memory = psutil.virtual_memory()
    if memory.percent > 90:
        health_status["status"] = "degraded"
        health_status["checks"]["memory"] = {
            "status": "warning",
            "message": f"High memory usage: {memory.percent}%"
        }
    else:
        health_status["checks"]["memory"] = {
            "status": "healthy",
            "message": f"Memory usage: {memory.percent}%"
        }
    
    # Disk health check
    disk = psutil.disk_usage('/')
    if disk.percent > 90:
        health_status["status"] = "degraded"
        health_status["checks"]["disk"] = {
            "status": "warning",
            "message": f"High disk usage: {disk.percent}%"
        }
    else:
        health_status["checks"]["disk"] = {
            "status": "healthy",
            "message": f"Disk usage: {disk.percent}%"
        }
    
    # CPU health check
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 90:
        health_status["status"] = "degraded"
        health_status["checks"]["cpu"] = {
            "status": "warning",
            "message": f"High CPU usage: {cpu_percent}%"
        }
    else:
        health_status["checks"]["cpu"] = {
            "status": "healthy",
            "message": f"CPU usage: {cpu_percent}%"
        }
    
    # LDAP health check (if enabled)
    if settings.LDAP_ENABLED:
        try:
            from app.services.ldap import ldap_service
            ldap_connected = await ldap_service.test_connection()
            if ldap_connected:
                health_status["checks"]["ldap"] = {
                    "status": "healthy",
                    "message": f"LDAP connected to {settings.LDAP_SERVER}:{settings.LDAP_PORT}"
                }
            else:
                health_status["status"] = "degraded"
                health_status["checks"]["ldap"] = {
                    "status": "unhealthy",
                    "message": "LDAP connection test failed"
                }
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["checks"]["ldap"] = {
                "status": "unhealthy",
                "message": f"LDAP error: {str(e)}"
            }
    
    return health_status


@router.get("/config", response_model=Dict[str, Any])
async def get_system_config(
    current_user: User = Depends(get_current_admin_user)
):
    """Get system configuration (admin only)"""
    
    # Return safe configuration values (no secrets)
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "api_prefix": settings.API_V1_PREFIX,
        "cors_origins": settings.CORS_ORIGINS,
        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
        "mcp_token_expire_hours": settings.MCP_TOKEN_EXPIRE_HOURS,
        "features": {
            "oauth_enabled": settings.OAUTH_ENABLED,
            "mfa_enabled": settings.MFA_ENABLED,
            "api_keys_enabled": settings.API_KEYS_ENABLED,
            "websockets_enabled": settings.WEBSOCKETS_ENABLED,
            "ldap_enabled": settings.LDAP_ENABLED
        },
        "limits": {
            "max_workspaces_per_user": settings.MAX_WORKSPACES_PER_USER,
            "max_lists_per_workspace": settings.MAX_LISTS_PER_WORKSPACE,
            "max_tasks_per_list": settings.MAX_TASKS_PER_LIST,
            "max_api_keys_per_user": settings.MAX_API_KEYS_PER_USER,
            "max_devices_per_user": settings.MAX_DEVICES_PER_USER
        },
        "ldap": {
            "enabled": settings.LDAP_ENABLED,
            "server": settings.LDAP_SERVER if settings.LDAP_ENABLED else None,
            "port": settings.LDAP_PORT if settings.LDAP_ENABLED else None,
            "use_ssl": settings.LDAP_USE_SSL if settings.LDAP_ENABLED else None,
            "base_dn": settings.LDAP_BASE_DN if settings.LDAP_ENABLED else None,
            "auto_create_user": settings.LDAP_AUTO_CREATE_USER if settings.LDAP_ENABLED else None
        }
    }