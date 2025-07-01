"""
Security middleware
Created: 2025-01-30 19:35:00 PST
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import re
import time
import hashlib
import hmac
from datetime import datetime
import ipaddress

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers"""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        # HSTS for HTTPS connections
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize incoming requests"""
    
    # Patterns for SQL injection detection
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|CREATE|ALTER)\b)",
        r"(--|#|\/\*|\*\/)",
        r"(\bOR\b\s*\d+\s*=\s*\d+)",
        r"(\bAND\b\s*\d+\s*=\s*\d+)",
        r"(\'|\"|;|\\x00|\\n|\\r|\\x1a)"
    ]
    
    # Patterns for XSS detection
    XSS_PATTERNS = [
        r"(<script[^>]*>.*?</script>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        r"(<iframe[^>]*>)",
        r"(<object[^>]*>)",
        r"(<embed[^>]*>)"
    ]
    
    # Maximum request sizes
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_URL_LENGTH = 2048
    
    async def dispatch(self, request: Request, call_next):
        """Validate request"""
        # Check URL length
        if len(str(request.url)) > self.MAX_URL_LENGTH:
            return JSONResponse(
                status_code=status.HTTP_414_REQUEST_URI_TOO_LONG,
                content={"detail": "Request URL too long"}
            )
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large"}
            )
        
        # Validate query parameters
        for param_name, param_value in request.query_params.items():
            if self._is_suspicious_input(str(param_value)):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": f"Invalid query parameter: {param_name}"}
                )
        
        # Process request
        return await call_next(request)
    
    def _is_suspicious_input(self, value: str) -> bool:
        """Check if input contains suspicious patterns"""
        value_lower = value.lower()
        
        # Check for SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        # Check for XSS patterns
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False


class RequestSignatureMiddleware(BaseHTTPMiddleware):
    """Verify request signatures for API key authentication"""
    
    def __init__(self, app, secret_key: str = None):
        super().__init__(app)
        self.secret_key = secret_key or settings.SECRET_KEY
    
    async def dispatch(self, request: Request, call_next):
        """Verify request signature if present"""
        # Skip signature check for public endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Check if signature is required (API key authentication)
        signature = request.headers.get("X-Signature")
        api_key = request.headers.get("X-API-Key")
        
        if api_key and not signature:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing request signature"}
            )
        
        if signature:
            # Verify signature
            timestamp = request.headers.get("X-Timestamp")
            if not timestamp:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Missing timestamp"}
                )
            
            # Check timestamp is recent (within 5 minutes)
            try:
                request_time = int(timestamp)
                current_time = int(time.time())
                if abs(current_time - request_time) > 300:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Request timestamp too old"}
                    )
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid timestamp"}
                )
            
            # Verify signature
            if not await self._verify_signature(request, signature, timestamp):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid signature"}
                )
        
        return await call_next(request)
    
    async def _verify_signature(
        self, 
        request: Request, 
        signature: str, 
        timestamp: str
    ) -> bool:
        """Verify request signature"""
        # Get request body
        body = await request.body()
        
        # Create signature string
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        
        signature_string = f"{method}\n{path}\n{query}\n{timestamp}\n{body.decode()}"
        
        # Calculate expected signature
        expected_signature = hmac.new(
            self.secret_key.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP whitelist middleware for admin endpoints"""
    
    def __init__(self, app, whitelist: list[str] = None):
        super().__init__(app)
        self.whitelist = whitelist or []
    
    async def dispatch(self, request: Request, call_next):
        """Check IP whitelist for admin endpoints"""
        # Only check whitelist for admin endpoints
        if not request.url.path.startswith("/api/v1/admin"):
            return await call_next(request)
        
        # Skip IP check for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip if no whitelist configured
        if not self.whitelist:
            return await call_next(request)
        
        # Get client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else None
        
        # Log the IP for debugging
        print(f"Admin endpoint accessed from IP: {client_ip}, Whitelist: {self.whitelist}")
        
        # Check whitelist
        if not self._is_ip_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": f"Access denied for IP: {client_ip}"}
            )
        
        return await call_next(request)
    
    def _is_ip_allowed(self, client_ip: str) -> bool:
        """Check if IP is in whitelist, supporting CIDR notation"""
        if not client_ip:
            return False
            
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
        except ValueError:
            return False
            
        for allowed_ip in self.whitelist:
            try:
                # Check if it's a CIDR notation
                if '/' in allowed_ip:
                    network = ipaddress.ip_network(allowed_ip, strict=False)
                    if client_ip_obj in network:
                        return True
                else:
                    # Direct IP comparison
                    if client_ip == allowed_ip:
                        return True
            except ValueError:
                # Invalid IP/CIDR format, skip
                continue
                
        return False


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log security-relevant events"""
    
    async def dispatch(self, request: Request, call_next):
        """Log request details"""
        start_time = time.time()
        
        # Get request details
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Process request
        response = await call_next(request)
        
        # Log security events
        if response.status_code >= 400:
            duration = time.time() - start_time
            
            # Log failed requests
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "ip": client_ip,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": duration,
                "user_agent": user_agent
            }
            
            # Log authentication failures specially
            if response.status_code == 401:
                print(f"AUTH_FAILURE: {log_entry}")
            elif response.status_code == 403:
                print(f"ACCESS_DENIED: {log_entry}")
            elif response.status_code >= 500:
                print(f"SERVER_ERROR: {log_entry}")
        
        return response