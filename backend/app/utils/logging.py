"""
Logging utilities
Created: 2025-01-30 20:15:00 PST
"""

import logging
import sys
from typing import Optional
import json
from datetime import datetime
from fastapi import Request

from app.config import settings


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging():
    """Configure application logging"""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with structured output
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.ENVIRONMENT == "production":
        # Use JSON formatting in production
        console_handler.setFormatter(StructuredFormatter())
    else:
        # Use readable format in development
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
    
    root_logger.addHandler(console_handler)
    
    # Reduce noise from some libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding context to log messages"""
    
    def __init__(self, logger: logging.Logger, extra: dict):
        super().__init__(logger, extra)
    
    def process(self, msg, kwargs):
        """Add extra context to all log messages"""
        kwargs["extra"] = {**self.extra, **kwargs.get("extra", {})}
        return msg, kwargs


def get_request_logger(request: Request, logger_name: str = __name__) -> LoggerAdapter:
    """Get a logger with request context"""
    logger = get_logger(logger_name)
    
    # Extract request info
    extra = {
        "request_id": request.headers.get("X-Request-ID", "unknown"),
        "method": request.method,
        "path": request.url.path,
        "ip_address": request.client.host if request.client else "unknown"
    }
    
    # Add user context if available
    if hasattr(request.state, "user_id"):
        extra["user_id"] = request.state.user_id
    
    return LoggerAdapter(logger, extra)


class SecurityLogger:
    """Logger for security events"""
    
    def __init__(self):
        self.logger = get_logger("security")
    
    def log_auth_failure(
        self,
        ip_address: str,
        email: Optional[str] = None,
        reason: str = "Invalid credentials"
    ):
        """Log authentication failure"""
        self.logger.warning(
            f"Authentication failure: {reason}",
            extra={
                "event_type": "auth_failure",
                "ip_address": ip_address,
                "email": email,
                "reason": reason
            }
        )
    
    def log_auth_success(
        self,
        user_id: str,
        ip_address: str,
        method: str = "password"
    ):
        """Log successful authentication"""
        self.logger.info(
            f"Authentication success for user {user_id}",
            extra={
                "event_type": "auth_success",
                "user_id": user_id,
                "ip_address": ip_address,
                "auth_method": method
            }
        )
    
    def log_access_denied(
        self,
        user_id: Optional[str],
        resource: str,
        ip_address: str,
        reason: str = "Insufficient permissions"
    ):
        """Log access denied event"""
        self.logger.warning(
            f"Access denied to {resource}: {reason}",
            extra={
                "event_type": "access_denied",
                "user_id": user_id,
                "resource": resource,
                "ip_address": ip_address,
                "reason": reason
            }
        )
    
    def log_rate_limit_exceeded(
        self,
        ip_address: str,
        endpoint: str,
        user_id: Optional[str] = None
    ):
        """Log rate limit exceeded"""
        self.logger.warning(
            f"Rate limit exceeded for {endpoint}",
            extra={
                "event_type": "rate_limit_exceeded",
                "ip_address": ip_address,
                "endpoint": endpoint,
                "user_id": user_id
            }
        )
    
    def log_suspicious_activity(
        self,
        ip_address: str,
        activity_type: str,
        details: dict
    ):
        """Log suspicious activity"""
        self.logger.error(
            f"Suspicious activity detected: {activity_type}",
            extra={
                "event_type": "suspicious_activity",
                "ip_address": ip_address,
                "activity_type": activity_type,
                "details": details
            }
        )


# Global security logger instance
security_logger = SecurityLogger()


class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self):
        self.logger = get_logger("performance")
    
    def log_slow_query(
        self,
        query: str,
        duration: float,
        threshold: float = 1.0
    ):
        """Log slow database query"""
        if duration > threshold:
            self.logger.warning(
                f"Slow query detected ({duration:.2f}s)",
                extra={
                    "event_type": "slow_query",
                    "query": query,
                    "duration": duration,
                    "threshold": threshold
                }
            )
    
    def log_slow_request(
        self,
        method: str,
        path: str,
        duration: float,
        status_code: int,
        threshold: float = 1.0
    ):
        """Log slow HTTP request"""
        if duration > threshold:
            self.logger.warning(
                f"Slow request: {method} {path} ({duration:.2f}s)",
                extra={
                    "event_type": "slow_request",
                    "method": method,
                    "path": path,
                    "duration": duration,
                    "status_code": status_code,
                    "threshold": threshold
                }
            )


# Global performance logger instance
performance_logger = PerformanceLogger()