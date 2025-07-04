"""
OAuth-related database models
Created: 2025-07-03 20:55:00 PST
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from uuid import uuid4
from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, 
    Text, JSON, Integer, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import secrets

from app.database import Base


class OAuthClient(Base):
    """OAuth 2.0 Client registration"""
    __tablename__ = "oauth_clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(String(255), unique=True, nullable=False, index=True)
    client_secret_hash = Column(String(255), nullable=True)  # Nullable for public clients
    client_name = Column(String(255), nullable=False)
    client_type = Column(String(50), nullable=False, default="confidential")  # confidential or public
    
    # Redirect URIs (stored as JSON array)
    redirect_uris = Column(JSON, default=list)
    allowed_scopes = Column(JSON, default=list)
    
    # Client metadata
    logo_uri = Column(Text, nullable=True)
    client_uri = Column(Text, nullable=True)
    policy_uri = Column(Text, nullable=True)
    tos_uri = Column(Text, nullable=True)
    
    # Owner information
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Dynamic registration support
    registration_access_token = Column(String(255), nullable=True)
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_user_id])
    authorization_codes = relationship("OAuthAuthorizationCode", back_populates="client", cascade="all, delete-orphan")
    tokens = relationship("OAuthToken", back_populates="client", cascade="all, delete-orphan")
    
    def verify_redirect_uri(self, redirect_uri: str) -> bool:
        """Verify if a redirect URI is allowed for this client"""
        if not self.redirect_uris:
            return False
        
        # For localhost with dynamic ports, allow pattern matching
        for allowed_uri in self.redirect_uris:
            if allowed_uri == redirect_uri:
                return True
            
            # Support dynamic localhost ports for Claude Desktop
            if "localhost" in allowed_uri and "localhost" in redirect_uri:
                # Extract base URL without port
                allowed_base = allowed_uri.split("://")[1].split(":")[0]
                redirect_base = redirect_uri.split("://")[1].split(":")[0]
                
                if allowed_base == redirect_base:
                    # Check if path matches
                    allowed_path = allowed_uri.split("/", 3)[-1] if "/" in allowed_uri.split("://")[1] else ""
                    redirect_path = redirect_uri.split("/", 3)[-1] if "/" in redirect_uri.split("://")[1] else ""
                    
                    if allowed_path == redirect_path:
                        return True
        
        return False


class OAuthAuthorizationCode(Base):
    """OAuth 2.0 Authorization codes (temporary)"""
    __tablename__ = "oauth_authorization_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(255), unique=True, nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("oauth_clients.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    redirect_uri = Column(Text, nullable=False)
    scope = Column(Text, nullable=True)
    
    # PKCE support
    code_challenge = Column(String(255), nullable=True)
    code_challenge_method = Column(String(10), nullable=True)  # S256 or plain
    
    # Expiration (codes should be short-lived, typically 10 minutes)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("OAuthClient", back_populates="authorization_codes")
    user = relationship("User")
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_used(self) -> bool:
        return self.used_at is not None
    
    def use(self):
        """Mark the authorization code as used"""
        self.used_at = datetime.utcnow()


class OAuthToken(Base):
    """OAuth 2.0 Access and Refresh tokens"""
    __tablename__ = "oauth_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    access_token_hash = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token_hash = Column(String(255), unique=True, nullable=True, index=True)
    
    client_id = Column(UUID(as_uuid=True), ForeignKey("oauth_clients.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Token metadata
    scope = Column(Text, nullable=True)
    token_type = Column(String(50), default="Bearer")
    
    # Expiration
    access_token_expires_at = Column(DateTime, nullable=False)
    refresh_token_expires_at = Column(DateTime, nullable=True)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Device/session information
    device_id = Column(String(255), nullable=True)
    device_name = Column(String(255), nullable=True)
    
    # MCP Agent association (for Claude Desktop integration)
    mcp_agent_id = Column(UUID(as_uuid=True), ForeignKey("mcp_agents.id"), nullable=True)
    
    # Relationships
    client = relationship("OAuthClient", back_populates="tokens")
    user = relationship("User")
    mcp_agent = relationship("MCPAgent")
    
    @property
    def is_access_token_expired(self) -> bool:
        return datetime.utcnow() > self.access_token_expires_at
    
    @property
    def is_refresh_token_expired(self) -> bool:
        if not self.refresh_token_expires_at:
            return False
        return datetime.utcnow() > self.refresh_token_expires_at
    
    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
    
    def revoke(self):
        """Revoke the token"""
        self.revoked_at = datetime.utcnow()
    
    def update_last_used(self):
        """Update the last used timestamp"""
        self.last_used_at = datetime.utcnow()
    
    @classmethod
    def generate_tokens(cls) -> Dict[str, str]:
        """Generate new access and refresh tokens"""
        return {
            "access_token": secrets.token_urlsafe(32),
            "refresh_token": secrets.token_urlsafe(32)
        }


# Create indexes for better performance
Index("idx_oauth_tokens_user_client", OAuthToken.user_id, OAuthToken.client_id)
Index("idx_oauth_codes_expires", OAuthAuthorizationCode.expires_at)
Index("idx_oauth_tokens_expires", OAuthToken.access_token_expires_at)