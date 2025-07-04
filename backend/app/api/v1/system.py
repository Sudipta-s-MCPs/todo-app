"""
System information and health API endpoints
Created: 2025-01-30 18:57:00 PST
"""

import os
import psutil
import platform
import time
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
        
        # Check if Redis client exists first
        if not redis_cache.redis_client:
            health_status["status"] = "degraded"
            health_status["checks"]["redis"] = {
                "status": "unhealthy",
                "message": "Redis client not initialized",
                "details": {
                    "connected": False,
                    "url": redis_cache._sanitize_url(str(settings.REDIS_URL)) if hasattr(redis_cache, '_sanitize_url') else "redis://***"
                }
            }
        elif await redis_cache.ping():
            # Get additional Redis info if available
            try:
                info = await redis_cache.redis_client.info()
                health_status["checks"]["redis"] = {
                    "status": "healthy",
                    "message": "Redis connection successful",
                    "details": {
                        "connected": True,
                        "version": info.get("redis_version", "unknown"),
                        "uptime_seconds": info.get("uptime_in_seconds", 0),
                        "connected_clients": info.get("connected_clients", 0),
                        "used_memory_human": info.get("used_memory_human", "unknown")
                    }
                }
            except:
                # Basic health check passed but couldn't get detailed info
                health_status["checks"]["redis"] = {
                    "status": "healthy",
                    "message": "Redis connection successful"
                }
        else:
            health_status["status"] = "degraded"
            health_status["checks"]["redis"] = {
                "status": "unhealthy",
                "message": "Redis ping failed",
                "details": {
                    "connected": False
                }
            }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis health check error: {str(e)}",
            "details": {
                "connected": False,
                "error": str(e)
            }
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
    # Check from database settings
    from app.services.settings_service import settings_service
    ldap_enabled_setting = await settings_service.get_setting("ldap_enabled", db)
    if ldap_enabled_setting and ldap_enabled_setting.value == "true":
        try:
            from app.services.ldap import ldap_service
            
            # Get LDAP settings from database
            ldap_server_setting = await settings_service.get_setting("ldap_server", db)
            ldap_port_setting = await settings_service.get_setting("ldap_port", db)
            
            # Get all LDAP settings from database
            ldap_config = {}
            ldap_settings = [
                'ldap_enabled', 'ldap_server', 'ldap_port', 'ldap_use_ssl', 
                'ldap_start_tls', 'ldap_bind_dn', 'ldap_bind_password', 
                'ldap_base_dn', 'ldap_user_search_base', 'ldap_user_filter',
                'ldap_user_attr_email', 'ldap_user_attr_name', 'ldap_user_attr_uid'
            ]
            
            for setting_key in ldap_settings:
                setting = await settings_service.get_setting(setting_key, db)
                if setting:
                    if setting_key == 'ldap_enabled':
                        ldap_config[setting_key] = setting.value == 'true'
                    elif setting_key == 'ldap_port':
                        ldap_config[setting_key] = int(setting.value) if setting.value else 389
                    elif setting_key in ['ldap_use_ssl', 'ldap_start_tls']:
                        ldap_config[setting_key] = setting.value == 'true'
                    else:
                        ldap_config[setting_key] = setting.value
            
            # Update ldap_service with database settings
            ldap_service.update_config(ldap_config)
            
            ldap_connected = await ldap_service.test_connection()
            if ldap_connected:
                health_status["checks"]["ldap"] = {
                    "status": "healthy",
                    "message": f"LDAP connected to {ldap_server_setting.value if ldap_server_setting else 'unknown'}:{ldap_port_setting.value if ldap_port_setting else 'unknown'}"
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


@router.get("/services-status", response_model=Dict[str, Any])
async def get_services_status(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Check connection status for external services (admin only)"""
    from app.services.settings_service import settings_service
    
    services_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check LDAP connection
    ldap_enabled = await settings_service.get_setting("ldap_enabled", db)
    if ldap_enabled and ldap_enabled.value == "true":
        try:
            ldap_server = await settings_service.get_setting("ldap_server", db)
            ldap_port = await settings_service.get_setting("ldap_port", db)
            
            if ldap_server and ldap_server.value:
                # Try to import and test LDAP connection
                try:
                    from app.services.ldap import ldap_service
                    
                    # Get all LDAP settings from database
                    ldap_config = {}
                    ldap_settings = [
                        'ldap_enabled', 'ldap_server', 'ldap_port', 'ldap_use_ssl', 
                        'ldap_start_tls', 'ldap_bind_dn', 'ldap_bind_password', 
                        'ldap_base_dn', 'ldap_user_search_base', 'ldap_user_filter',
                        'ldap_user_attr_email', 'ldap_user_attr_name', 'ldap_user_attr_uid'
                    ]
                    
                    for setting_key in ldap_settings:
                        setting = await settings_service.get_setting(setting_key, db)
                        if setting:
                            if setting_key == 'ldap_enabled':
                                ldap_config[setting_key] = setting.value == 'true'
                            elif setting_key == 'ldap_port':
                                ldap_config[setting_key] = int(setting.value) if setting.value else 389
                            elif setting_key in ['ldap_use_ssl', 'ldap_start_tls']:
                                ldap_config[setting_key] = setting.value == 'true'
                            else:
                                ldap_config[setting_key] = setting.value
                    
                    # Update ldap_service with database settings
                    ldap_service.update_config(ldap_config)
                    
                    connected = await ldap_service.test_connection()
                    services_status["services"]["ldap"] = {
                        "enabled": True,
                        "connected": connected,
                        "message": f"Connected to {ldap_server.value}:{ldap_port.value}" if connected else "Connection failed",
                        "endpoint": f"{ldap_server.value}:{ldap_port.value}"
                    }
                except Exception as e:
                    services_status["services"]["ldap"] = {
                        "enabled": True,
                        "connected": False,
                        "message": f"Error: {str(e)}",
                        "endpoint": f"{ldap_server.value}:{ldap_port.value if ldap_port else '389'}"
                    }
            else:
                services_status["services"]["ldap"] = {
                    "enabled": True,
                    "connected": False,
                    "message": "LDAP server not configured",
                    "endpoint": None
                }
        except Exception as e:
            services_status["services"]["ldap"] = {
                "enabled": True,
                "connected": False,
                "message": f"Configuration error: {str(e)}",
                "endpoint": None
            }
    else:
        services_status["services"]["ldap"] = {
            "enabled": False,
            "connected": False,
            "message": "LDAP authentication disabled",
            "endpoint": None
        }
    
    # Check MinIO connection
    minio_endpoint = await settings_service.get_setting("minio_endpoint", db)
    if minio_endpoint and minio_endpoint.value:
        try:
            from minio import Minio
            
            minio_access_key = await settings_service.get_setting("minio_access_key", db)
            minio_secret_key = await settings_service.get_setting("minio_secret_key", db)
            minio_secure = await settings_service.get_setting("minio_secure", db)
            
            if minio_access_key and minio_secret_key:
                client = Minio(
                    minio_endpoint.value,
                    access_key=minio_access_key.value,
                    secret_key=minio_secret_key.value,
                    secure=minio_secure.value == "true" if minio_secure else False
                )
                
                # Try to list buckets as a connection test
                try:
                    buckets = client.list_buckets()
                    services_status["services"]["minio"] = {
                        "enabled": True,
                        "connected": True,
                        "message": f"Connected - {len(buckets)} buckets available",
                        "endpoint": minio_endpoint.value
                    }
                except Exception as e:
                    services_status["services"]["minio"] = {
                        "enabled": True,
                        "connected": False,
                        "message": f"Connection failed: {str(e)}",
                        "endpoint": minio_endpoint.value
                    }
            else:
                services_status["services"]["minio"] = {
                    "enabled": True,
                    "connected": False,
                    "message": "MinIO credentials not configured",
                    "endpoint": minio_endpoint.value
                }
        except ImportError:
            services_status["services"]["minio"] = {
                "enabled": False,
                "connected": False,
                "message": "MinIO client not installed",
                "endpoint": minio_endpoint.value
            }
        except Exception as e:
            services_status["services"]["minio"] = {
                "enabled": False,
                "connected": False,
                "message": f"Error: {str(e)}",
                "endpoint": minio_endpoint.value
            }
    else:
        services_status["services"]["minio"] = {
            "enabled": False,
            "connected": False,
            "message": "MinIO not configured",
            "endpoint": None
        }
    
    # Check Qdrant connection
    qdrant_host = await settings_service.get_setting("qdrant_host", db)
    if qdrant_host and qdrant_host.value:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.exceptions import UnexpectedResponse
            
            qdrant_port = await settings_service.get_setting("qdrant_port", db)
            qdrant_api_key = await settings_service.get_setting("qdrant_api_key", db)
            
            # Use URL format instead of host/port for better compatibility
            qdrant_url = f"http://{qdrant_host.value}:{qdrant_port.value if qdrant_port else '6333'}"
            
            client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key.value if qdrant_api_key and qdrant_api_key.value else None,
                timeout=10  # Add timeout
            )
            
            # Try to get collections as a connection test
            try:
                collections = client.get_collections()
                services_status["services"]["qdrant"] = {
                    "enabled": True,
                    "connected": True,
                    "message": f"Connected - {len(collections.collections)} collections available",
                    "endpoint": f"{qdrant_host.value}:{qdrant_port.value if qdrant_port else '6333'}"
                }
            except UnexpectedResponse as e:
                services_status["services"]["qdrant"] = {
                    "enabled": True,
                    "connected": False,
                    "message": f"Connection failed: {e.status_code} - {e.reason_phrase}",
                    "endpoint": f"{qdrant_host.value}:{qdrant_port.value if qdrant_port else '6333'}"
                }
            except Exception as e:
                services_status["services"]["qdrant"] = {
                    "enabled": True,
                    "connected": False,
                    "message": f"Connection failed: {str(e)}",
                    "endpoint": f"{qdrant_host.value}:{qdrant_port.value if qdrant_port else '6333'}"
                }
        except ImportError:
            services_status["services"]["qdrant"] = {
                "enabled": False,
                "connected": False,
                "message": "Qdrant client not installed",
                "endpoint": f"{qdrant_host.value}:{qdrant_port.value if qdrant_port else '6333'}"
            }
        except Exception as e:
            services_status["services"]["qdrant"] = {
                "enabled": False,
                "connected": False,
                "message": f"Error: {str(e)}",
                "endpoint": qdrant_host.value
            }
    else:
        services_status["services"]["qdrant"] = {
            "enabled": False,
            "connected": False,
            "message": "Qdrant not configured",
            "endpoint": None
        }
    
    # Check Groq AI connection
    groq_api_key = await settings_service.get_setting("groq_api_key", db)
    if groq_api_key and groq_api_key.value:
        try:
            import httpx
            
            # Test Groq API with a simple request
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {groq_api_key.value}"},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    models = response.json()
                    services_status["services"]["groq"] = {
                        "enabled": True,
                        "connected": True,
                        "message": f"Connected - {len(models.get('data', []))} models available",
                        "endpoint": "api.groq.com"
                    }
                else:
                    services_status["services"]["groq"] = {
                        "enabled": True,
                        "connected": False,
                        "message": f"API error: {response.status_code}",
                        "endpoint": "api.groq.com"
                    }
        except Exception as e:
            services_status["services"]["groq"] = {
                "enabled": True,
                "connected": False,
                "message": f"Connection failed: {str(e)}",
                "endpoint": "api.groq.com"
            }
    else:
        services_status["services"]["groq"] = {
            "enabled": False,
            "connected": False,
            "message": "Groq API key not configured",
            "endpoint": None
        }
    
    # Check HuggingFace AI connection using new Inference Providers API
    huggingface_token = await settings_service.get_setting("huggingface_api_token", db)
    huggingface_model = await settings_service.get_setting("huggingface_model", db)
    huggingface_provider = await settings_service.get_setting("huggingface_provider", db)
    
    if huggingface_token and huggingface_token.value and huggingface_model and huggingface_model.value:
        try:
            from huggingface_hub import InferenceClient
            
            model_name = huggingface_model.value
            provider = huggingface_provider.value if huggingface_provider and huggingface_provider.value else "auto"
            endpoint = f"Inference Providers ({provider})" if provider != "auto" else "Inference Providers (auto)"
            
            # Create InferenceClient with proper provider support
            if provider == "auto":
                client = InferenceClient(provider="auto", token=huggingface_token.value)
            else:
                client = InferenceClient(
                    provider=provider,
                    token=huggingface_token.value
                )
            
            # Test with a minimal request
            test_messages = [{"role": "user", "content": "Hello"}]
            completion = client.chat_completion(
                messages=test_messages,
                model=model_name,
                max_tokens=1,
                temperature=0.1
            )
            
            # If we get here, the connection is successful
            services_status["services"]["huggingface"] = {
                "enabled": True,
                "connected": True,
                "message": f"Connected - Model: {model_name}",
                "endpoint": endpoint
            }
            
        except ImportError:
            services_status["services"]["huggingface"] = {
                "enabled": False,
                "connected": False,
                "message": "huggingface_hub library not available or outdated",
                "endpoint": None
            }
        except Exception as e:
            error_msg = str(e).lower()
            endpoint = f"Inference Providers ({provider})" if provider != "auto" else "Inference Providers (auto)"
            
            # Handle specific error cases
            if "not supported by any provider" in error_msg:
                services_status["services"]["huggingface"] = {
                    "enabled": True,
                    "connected": False,
                    "message": f"Model not supported by enabled providers - {model_name}. Check https://hf.co/settings/inference-providers",
                    "endpoint": endpoint
                }
            elif "rate limit" in error_msg or "429" in error_msg:
                services_status["services"]["huggingface"] = {
                    "enabled": True,
                    "connected": True,  # Rate limit means service is working
                    "message": f"Rate limited - {model_name}",
                    "endpoint": endpoint
                }
            elif "authentication" in error_msg or "401" in error_msg:
                services_status["services"]["huggingface"] = {
                    "enabled": True,
                    "connected": False,
                    "message": "Authentication failed - check API token",
                    "endpoint": endpoint
                }
            elif "loading" in error_msg or "503" in error_msg:
                services_status["services"]["huggingface"] = {
                    "enabled": True,
                    "connected": True,  # Loading means service is working
                    "message": f"Model loading - {model_name}",
                    "endpoint": endpoint
                }
            elif "paused" in error_msg or "endpoint is paused" in error_msg:
                services_status["services"]["huggingface"] = {
                    "enabled": True,
                    "connected": True,  # Paused means service is working but endpoint needs activation
                    "message": f"Model endpoint paused - {model_name} (will activate on use)",
                    "endpoint": endpoint
                }
            elif "timeout" in error_msg:
                services_status["services"]["huggingface"] = {
                    "enabled": True,
                    "connected": False,
                    "message": f"Request timeout - {model_name}",
                    "endpoint": endpoint
                }
            else:
                services_status["services"]["huggingface"] = {
                    "enabled": True,
                    "connected": False,
                    "message": f"Connection failed: {str(e)[:80]}...",
                    "endpoint": endpoint
                }
    else:
        missing_parts = []
        if not huggingface_token or not huggingface_token.value:
            missing_parts.append("API token")
        if not huggingface_model or not huggingface_model.value:
            missing_parts.append("model")
        
        services_status["services"]["huggingface"] = {
            "enabled": False,
            "connected": False,
            "message": f"Missing: {', '.join(missing_parts)}",
            "endpoint": None
        }
    
    # Check Gemini AI connection
    gemini_api_key = await settings_service.get_setting("gemini_api_key", db)
    if gemini_api_key and gemini_api_key.value:
        try:
            import httpx
            
            # Test Gemini API with a simple request to list models
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_api_key.value}",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    models = response.json()
                    model_count = len(models.get('models', []))
                    services_status["services"]["gemini"] = {
                        "enabled": True,
                        "connected": True,
                        "message": f"Connected - {model_count} models available",
                        "endpoint": "generativelanguage.googleapis.com"
                    }
                else:
                    services_status["services"]["gemini"] = {
                        "enabled": True,
                        "connected": False,
                        "message": f"API error: {response.status_code}",
                        "endpoint": "generativelanguage.googleapis.com"
                    }
        except Exception as e:
            services_status["services"]["gemini"] = {
                "enabled": True,
                "connected": False,
                "message": f"Connection failed: {str(e)}",
                "endpoint": "generativelanguage.googleapis.com"
            }
    else:
        services_status["services"]["gemini"] = {
            "enabled": False,
            "connected": False,
            "message": "Gemini API key not configured",
            "endpoint": None
        }
    
    return services_status


@router.get("/redis-status", response_model=Dict[str, Any])
async def get_redis_status(
    current_user: User = Depends(get_current_admin_user)
):
    """Get detailed Redis connection status and statistics (admin only)"""
    from app.services.cache import redis_cache
    
    redis_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "connection": {
            "url": redis_cache._sanitize_url(str(settings.REDIS_URL)) if hasattr(redis_cache, '_sanitize_url') else "redis://***",
            "connected": False,
            "client_exists": redis_cache.redis_client is not None
        },
        "statistics": {},
        "performance": {}
    }
    
    if not redis_cache.redis_client:
        redis_status["connection"]["message"] = "Redis client not initialized"
        return redis_status
    
    try:
        # Test connection
        start_time = time.time()
        await redis_cache.redis_client.ping()
        ping_time = (time.time() - start_time) * 1000  # Convert to ms
        
        redis_status["connection"]["connected"] = True
        redis_status["connection"]["message"] = "Connected"
        redis_status["performance"]["ping_ms"] = round(ping_time, 2)
        
        # Get Redis info
        info = await redis_cache.redis_client.info()
        
        # Extract key statistics
        redis_status["statistics"] = {
            "version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "uptime_days": info.get("uptime_in_days", 0),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "used_memory_peak_human": info.get("used_memory_peak_human", "unknown"),
            "total_connections_received": info.get("total_connections_received", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "evicted_keys": info.get("evicted_keys", 0),
            "expired_keys": info.get("expired_keys", 0)
        }
        
        # Calculate hit rate
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        if hits + misses > 0:
            redis_status["statistics"]["hit_rate_percent"] = round((hits / (hits + misses)) * 100, 2)
        
        # Get database stats
        db_stats = {}
        for key, value in info.items():
            if key.startswith("db"):
                db_stats[key] = value
        redis_status["statistics"]["databases"] = db_stats
        
    except Exception as e:
        redis_status["connection"]["connected"] = False
        redis_status["connection"]["message"] = f"Connection error: {str(e)}"
        redis_status["connection"]["error"] = str(e)
    
    return redis_status


@router.get("/config", response_model=Dict[str, Any])
async def get_system_config(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system configuration (admin only)"""
    from app.services.settings_service import settings_service
    
    # Get feature flags from database
    mfa_enabled_setting = await settings_service.get_setting("mfa_enabled", db)
    api_keys_enabled_setting = await settings_service.get_setting("api_keys_enabled", db)
    websockets_enabled_setting = await settings_service.get_setting("websockets_enabled", db)
    ldap_enabled_setting = await settings_service.get_setting("ldap_enabled", db)
    
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
            "oauth_enabled": settings.OAUTH_ENABLED,  # OAuth remains from env as it's not in DB settings
            "mfa_enabled": mfa_enabled_setting.value == "true" if mfa_enabled_setting else settings.MFA_ENABLED,
            "api_keys_enabled": api_keys_enabled_setting.value == "true" if api_keys_enabled_setting else settings.API_KEYS_ENABLED,
            "websockets_enabled": websockets_enabled_setting.value == "true" if websockets_enabled_setting else settings.WEBSOCKETS_ENABLED,
            "ldap_enabled": ldap_enabled_setting.value == "true" if ldap_enabled_setting else settings.LDAP_ENABLED
        },
        "limits": {
            "max_workspaces_per_user": settings.MAX_WORKSPACES_PER_USER,
            "max_lists_per_workspace": settings.MAX_LISTS_PER_WORKSPACE,
            "max_tasks_per_list": settings.MAX_TASKS_PER_LIST,
            "max_api_keys_per_user": settings.MAX_API_KEYS_PER_USER,
            "max_devices_per_user": settings.MAX_DEVICES_PER_USER
        },
        "ldap": {
            "enabled": ldap_enabled_setting.value == "true" if ldap_enabled_setting else settings.LDAP_ENABLED,
            "server": (await settings_service.get_setting("ldap_server", db)).value if ldap_enabled_setting and ldap_enabled_setting.value == "true" else None,
            "port": int((await settings_service.get_setting("ldap_port", db)).value) if ldap_enabled_setting and ldap_enabled_setting.value == "true" else None,
            "use_ssl": (await settings_service.get_setting("ldap_use_ssl", db)).value == "true" if ldap_enabled_setting and ldap_enabled_setting.value == "true" else None,
            "base_dn": (await settings_service.get_setting("ldap_base_dn", db)).value if ldap_enabled_setting and ldap_enabled_setting.value == "true" else None,
            "auto_create_user": (await settings_service.get_setting("ldap_auto_create_user", db)).value == "true" if ldap_enabled_setting and ldap_enabled_setting.value == "true" else None
        }
    }