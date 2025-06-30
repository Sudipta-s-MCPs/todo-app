"""
Security utilities for authentication and authorization
Created: 2025-01-30 14:08:00 PST
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import string
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib

from app.config import settings
from app.models.user import User, APIKey

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
MCP_TOKEN_EXPIRE_HOURS = settings.MCP_TOKEN_EXPIRE_HOURS


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def generate_token(length: int = 32) -> str:
    """Generate a secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_api_key() -> tuple[str, str]:
    """
    Generate an API key and its hash
    Returns: (plain_key, key_hash)
    """
    prefix = "sk_todo_"
    key = prefix + generate_token(40)
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_mcp_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT token for MCP agents"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=MCP_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire, "type": "mcp"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Invalid token")


async def verify_api_key(
    db: AsyncSession, 
    api_key: str
) -> Optional[APIKey]:
    """Verify an API key and return the associated APIKey object"""
    key_hash = hash_api_key(api_key)
    
    result = await db.execute(
        select(APIKey)
        .where(APIKey.key_hash == key_hash)
        .where(APIKey.is_active == True)
    )
    api_key_obj = result.scalar_one_or_none()
    
    if api_key_obj and (
        api_key_obj.expires_at is None or 
        api_key_obj.expires_at > datetime.utcnow()
    ):
        return api_key_obj
    
    return None


def generate_totp_secret() -> str:
    """Generate a TOTP secret for 2FA"""
    return secrets.token_hex(16)


def calculate_similarity_hash(title: str, description: Optional[str] = None) -> str:
    """
    Calculate a hash for duplicate detection based on title and description
    """
    # Normalize text
    normalized_title = title.lower().strip()
    normalized_desc = (description or "").lower().strip()
    
    # Combine and hash
    combined = f"{normalized_title}:{normalized_desc}"
    return hashlib.sha256(combined.encode()).hexdigest()