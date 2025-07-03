"""
Authentication API endpoints
Created: 2025-01-30 14:14:00 PST
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
import pyotp
import qrcode
import io
import base64
import hashlib
from PIL import Image

from app.database import get_db
from app.models.user import User, UserDevice, UserSession, APIKey, MCPAgent, DeviceType, AccessMethod
from app.models.activity import ActivityLog, ActionType, ResourceType
from app.config import settings
from app.services.dynamic_settings import dynamic_settings
from app.schemas.auth import (
    UserRegister, UserLogin, Token, TokenRefresh, LoginResponse, PasswordReset,
    PasswordResetConfirm, PasswordChange, DeviceInfo, APIKeyCreate,
    APIKeyResponse, APIKeyInfo, MCPAgentRegister, MCPAgentResponse,
    MCPAgentInfo, TwoFactorEnable, TwoFactorConfirm, UserInfo
)
from app.api.deps import get_current_user, get_access_info, get_access_info_direct, get_current_admin_user, is_admin_user
from app.utils.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, create_mcp_token, decode_token,
    generate_api_key, generate_totp_secret, generate_token
)
from app.services.activity import log_activity
from app.middleware import rate_limit
from app.utils.logging import security_logger
from app.services.ldap import ldap_service, create_user_from_ldap, sync_user_from_ldap

router = APIRouter()


@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
@rate_limit(requests_per_minute=5)  # Limit registration attempts
async def register(
    request: Request,
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=get_password_hash(user_data.password),
        timezone=user_data.timezone,
        locale=user_data.locale,
        approval_status="pending"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Log activity
    await log_activity(
        db=db,
        user_id=user.id,
        action_type=ActionType.REGISTER.value,
        resource_type=ResourceType.USER,
        resource_id=user.id,
        access_method=AccessMethod.WEB,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    return user


@router.post("/login", response_model=LoginResponse)
@rate_limit(requests_per_minute=10)  # Limit login attempts
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login with email/username and password (supports LDAP)"""
    # Try to find user by email or external_id (for LDAP users)
    result = await db.execute(
        select(User).where(
            or_(
                User.email == form_data.username,
                User.external_id == form_data.username
            )
        )
    )
    user = result.scalar_one_or_none()
    
    # Check if LDAP is enabled
    if ldap_service.ldap_enabled:
        # If user doesn't exist or is an LDAP user, try LDAP authentication
        if not user or user.auth_provider == "ldap":
            ldap_result = await ldap_service.authenticate(
                form_data.username,
                form_data.password
            )
            
            if ldap_result.success and ldap_result.user_info:
                if not user:
                    # Auto-create user from LDAP if enabled
                    if dynamic_settings.LDAP_AUTO_CREATE_USER:
                        user = await create_user_from_ldap(ldap_result.user_info, db)
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="User not registered. Please contact administrator."
                        )
                else:
                    # Sync user data from LDAP
                    await sync_user_from_ldap(user, ldap_result.user_info)
                    await db.commit()
            elif user and user.auth_provider == "ldap":
                # LDAP user but LDAP auth failed
                security_logger.log_auth_failure(
                    ip_address=request.client.host,
                    email=form_data.username,
                    reason="LDAP authentication failed"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid LDAP credentials"
                )
            # If LDAP auth failed but user is local, fall through to local auth
    
    # Local authentication (if not LDAP user or LDAP disabled)
    if user and user.auth_provider == "local":
        if not user.password_hash or not verify_password(form_data.password, user.password_hash):
            security_logger.log_auth_failure(
                ip_address=request.client.host,
                email=form_data.username,
                reason="Invalid credentials"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
    elif not user:
        # User doesn't exist and LDAP didn't create one
        security_logger.log_auth_failure(
            ip_address=request.client.host,
            email=form_data.username,
            reason="User not found"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        security_logger.log_auth_failure(
            ip_address=request.client.host,
            email=form_data.username,
            reason="Account inactive"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Check if user is approved
    if user.approval_status != "approved" and not user.is_admin:
        security_logger.log_auth_failure(
            ip_address=request.client.host,
            email=form_data.username,
            reason="Account pending approval"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval. You will receive an email once your account is approved."
        )
    
    # Get device info from headers
    device_name = request.headers.get("X-Device-Name", "Unknown Device")
    device_type = DeviceType(request.headers.get("X-Device-Type", "web"))
    device_identifier = request.headers.get("X-Device-ID", generate_token(16))
    
    # Find or create device
    result = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == user.id,
            UserDevice.device_identifier == device_identifier
        )
    )
    device = result.scalar_one_or_none()
    
    if not device:
        device = UserDevice(
            user_id=user.id,
            device_name=device_name,
            device_type=device_type,
            device_identifier=device_identifier,
            last_ip_address=request.client.host
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
    else:
        device.last_used_at = datetime.utcnow()
        device.last_ip_address = request.client.host
    
    # Create session
    session = UserSession(
        user_id=user.id,
        device_id=device.id,
        session_token=generate_token(32),
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        access_method=AccessMethod.WEB,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    
    # Update user last active
    user.last_active_at = datetime.utcnow()
    
    await db.commit()
    
    # Create tokens
    access_token = create_access_token(data={
        "sub": str(user.id),
        "session_id": str(session.id),
        "device_id": str(device.id)
    })
    refresh_token = create_refresh_token(data={
        "sub": str(user.id),
        "session_id": str(session.id)
    })
    
    # Log activity
    await log_activity(
        db=db,
        user_id=user.id,
        action_type=ActionType.LOGIN,
        resource_type=ResourceType.SESSION,
        resource_id=session.id,
        device_id=device.id,
        session_id=session.id,
        access_method=AccessMethod.WEB,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    # Log successful authentication
    security_logger.log_auth_success(
        user_id=str(user.id),
        ip_address=request.client.host,
        method="password"
    )
    
    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserInfo(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            timezone=user.timezone,
            locale=user.locale,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_admin=is_admin_user(user),
            approval_status=user.approval_status,
            two_factor_enabled=user.two_factor_enabled,
            auth_provider=user.auth_provider,
            created_at=user.created_at,
            last_active_at=user.last_active_at
        )
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token"""
    try:
        payload = decode_token(token_data.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        
        user_id = payload.get("sub")
        session_id = payload.get("session_id")
        
        # Verify session is still active
        result = await db.execute(
            select(UserSession).where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        # Update session activity
        session.last_activity_at = datetime.utcnow()
        
        # Create new tokens
        access_token = create_access_token(data={
            "sub": user_id,
            "session_id": session_id,
            "device_id": str(session.device_id) if session.device_id else None
        })
        
        new_refresh_token = create_refresh_token(data={
            "sub": user_id,
            "session_id": session_id
        })
        
        await db.commit()
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout current session"""
    # Get session from token
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        try:
            payload = decode_token(token)
            session_id = payload.get("session_id")
            
            if session_id:
                result = await db.execute(
                    select(UserSession).where(
                        UserSession.id == session_id,
                        UserSession.user_id == current_user.id
                    )
                )
                session = result.scalar_one_or_none()
                
                if session:
                    session.is_active = False
                    
                    # Log activity
                    await log_activity(
                        db=db,
                        user_id=current_user.id,
                        action_type=ActionType.LOGOUT.value,
                        resource_type=ResourceType.SESSION,
                        resource_id=session.id,
                        device_id=session.device_id,
                        session_id=session.id,
                        access_method=AccessMethod.WEB,
                        ip_address=request.client.host,
                        user_agent=request.headers.get("User-Agent")
                    )
                    
                    await db.commit()
                    
        except (ValueError, KeyError):
            pass
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.put("/me", response_model=UserInfo)
async def update_user_info(
    request: Request,
    name: Optional[str] = None,
    timezone: Optional[str] = None,
    locale: Optional[str] = None,
    avatar_url: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user information"""
    if name:
        current_user.name = name
    if timezone:
        current_user.timezone = timezone
    if locale:
        current_user.locale = locale
    if avatar_url is not None:
        current_user.avatar_url = avatar_url
    
    current_user.updated_at = datetime.utcnow()
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.PROFILE_UPDATE.value,
        resource_type=ResourceType.USER,
        resource_id=current_user.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    current_user.password_hash = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    
    # Invalidate all sessions except current
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    current_session_id = None
    if token:
        try:
            payload = decode_token(token)
            current_session_id = payload.get("session_id")
        except:
            pass
    
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        )
    )
    sessions = result.scalars().all()
    
    for session in sessions:
        if str(session.id) != current_session_id:
            session.is_active = False
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.PASSWORD_CHANGE.value,
        resource_type=ResourceType.USER,
        resource_id=current_user.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload user avatar"""
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Validate file size (max 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be less than 5MB"
        )
    
    # Validate image format
    try:
        image = Image.open(io.BytesIO(contents))
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (max 512x512)
        max_size = (512, 512)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to base64 data URL
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        avatar_url = f"data:image/jpeg;base64,{img_base64}"
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format"
        )
    
    # Update user avatar
    current_user.avatar_url = avatar_url
    current_user.updated_at = datetime.utcnow()
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.PROFILE_UPDATE.value,
        resource_type=ResourceType.USER,
        resource_id=current_user.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={"action": "avatar_upload"}
    )
    
    await db.commit()
    await db.refresh(current_user)
    
    return {"avatar_url": current_user.avatar_url}


@router.get("/devices", response_model=list[DeviceInfo])
async def get_user_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user devices"""
    result = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == current_user.id,
            UserDevice.is_active == True
        ).order_by(UserDevice.last_used_at.desc())
    )
    devices = result.scalars().all()
    
    return [DeviceInfo.model_validate(device) for device in devices]


@router.delete("/devices/{device_id}")
async def remove_device(
    device_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a user device"""
    result = await db.execute(
        select(UserDevice).where(
            UserDevice.id == device_id,
            UserDevice.user_id == current_user.id
        )
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Don't allow removing current device
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        try:
            payload = decode_token(token)
            current_device_id = payload.get("device_id")
            if str(device.id) == current_device_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove current device"
                )
        except:
            pass
    
    device.is_active = False
    
    # Invalidate all sessions for this device
    result = await db.execute(
        select(UserSession).where(
            UserSession.device_id == device.id,
            UserSession.is_active == True
        )
    )
    sessions = result.scalars().all()
    
    for session in sessions:
        session.is_active = False
    
    # Log activity
    access_method, current_device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.DEVICE_REMOVE.value,
        resource_type=ResourceType.DEVICE,
        resource_id=device.id,
        device_id=current_device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    await db.commit()
    
    return {"message": "Device removed successfully"}


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: Request,
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new API key"""
    # Generate key
    plain_key, key_hash = generate_api_key()
    
    # Calculate expiration
    expires_at = None
    if key_data.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_days)
    
    # Create API key
    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=key_data.name,
        permissions=key_data.permissions,
        rate_limit=key_data.rate_limit,
        expires_at=expires_at
    )
    db.add(api_key)
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.API_KEY_CREATE.value,
        resource_type=ResourceType.API_KEY,
        resource_id=api_key.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={"name": key_data.name}
    )
    
    await db.commit()
    await db.refresh(api_key)
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=plain_key,  # Only returned on creation
        permissions=api_key.permissions,
        rate_limit=api_key.rate_limit,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at
    )


@router.get("/api-keys", response_model=list[APIKeyInfo])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all user API keys"""
    result = await db.execute(
        select(APIKey).where(
            APIKey.user_id == current_user.id,
            APIKey.is_active == True
        ).order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()
    
    return [APIKeyInfo.model_validate(key) for key in api_keys]


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key"""
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.API_KEY_DELETE.value,
        resource_type=ResourceType.API_KEY,
        resource_id=api_key.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    await db.commit()
    
    return {"message": "API key deleted successfully"}


@router.post("/mcp/register", response_model=MCPAgentResponse, status_code=status.HTTP_201_CREATED)
async def register_mcp_agent(
    request: Request,
    agent_data: MCPAgentRegister,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Register a new MCP agent"""
    # Generate unique identifier
    agent_identifier = f"mcp_{generate_token(16)}"
    
    # Create MCP agent
    mcp_agent = MCPAgent(
        user_id=current_user.id,
        agent_name=agent_data.agent_name,
        agent_identifier=agent_identifier,
        capabilities=agent_data.capabilities,
        permissions=agent_data.permissions
    )
    db.add(mcp_agent)
    
    # Create API key for the agent
    plain_key, key_hash = generate_api_key()
    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=f"MCP: {agent_data.agent_name}",
        permissions=agent_data.permissions,
        rate_limit=10000,  # Higher rate limit for MCP agents
        expires_at=None  # MCP keys don't expire
    )
    db.add(api_key)
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.MCP_AGENT_REGISTER.value,
        resource_type=ResourceType.MCP_AGENT,
        resource_id=mcp_agent.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={"agent_name": agent_data.agent_name}
    )
    
    await db.commit()
    await db.refresh(mcp_agent)
    
    return MCPAgentResponse(
        id=mcp_agent.id,
        agent_name=mcp_agent.agent_name,
        agent_identifier=mcp_agent.agent_identifier,
        api_key=plain_key,  # Only returned on creation
        capabilities=mcp_agent.capabilities,
        permissions=mcp_agent.permissions,
        created_at=mcp_agent.created_at
    )


@router.get("/mcp/agents", response_model=list[MCPAgentInfo])
async def list_mcp_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all MCP agents"""
    result = await db.execute(
        select(MCPAgent).where(
            MCPAgent.user_id == current_user.id,
            MCPAgent.is_active == True
        ).order_by(MCPAgent.created_at.desc())
    )
    agents = result.scalars().all()
    
    return [MCPAgentInfo.model_validate(agent) for agent in agents]


@router.post("/mcp/heartbeat")
async def mcp_heartbeat(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update MCP agent heartbeat"""
    # Get agent ID from token or API key
    access_method, _, _, api_key_id, mcp_agent_id = await get_access_info_direct(
        request, db
    )
    
    if not mcp_agent_id:
        # Try to find agent by API key
        if api_key_id:
            result = await db.execute(
                select(APIKey).where(APIKey.id == api_key_id)
            )
            api_key = result.scalar_one_or_none()
            if api_key and "mcp" in api_key.name.lower():
                # Find associated MCP agent
                result = await db.execute(
                    select(MCPAgent).where(
                        MCPAgent.user_id == current_user.id,
                        MCPAgent.is_active == True
                    ).order_by(MCPAgent.created_at.desc())
                )
                agent = result.scalar_one_or_none()
                if agent:
                    mcp_agent_id = agent.id
    
    if mcp_agent_id:
        result = await db.execute(
            select(MCPAgent).where(
                MCPAgent.id == mcp_agent_id,
                MCPAgent.user_id == current_user.id
            )
        )
        agent = result.scalar_one_or_none()
        
        if agent:
            agent.last_heartbeat = datetime.utcnow()
            await db.commit()
            return {"status": "ok"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="MCP agent not found"
    )


@router.post("/2fa/enable", response_model=dict)
async def enable_two_factor(
    request: Request,
    data: TwoFactorEnable,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable two-factor authentication"""
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication already enabled"
        )
    
    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Generate TOTP secret
    secret = generate_totp_secret()
    current_user.totp_secret = secret
    
    # Generate QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name="Smart-ToDo"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    qr_code_base64 = base64.b64encode(buf.getvalue()).decode()
    
    await db.commit()
    
    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_code_base64}"
    }


@router.post("/2fa/confirm")
async def confirm_two_factor(
    request: Request,
    data: TwoFactorConfirm,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Confirm two-factor authentication setup"""
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication already enabled"
        )
    
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor setup not initiated"
        )
    
    # Verify TOTP code
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(data.totp_code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    current_user.two_factor_enabled = True
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.TWO_FACTOR_ENABLE.value,
        resource_type=ResourceType.USER,
        resource_id=current_user.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    await db.commit()
    
    return {"message": "Two-factor authentication enabled successfully"}


@router.post("/ldap/sync")
async def sync_ldap_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sync current user data from LDAP"""
    if not ldap_service.ldap_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LDAP authentication is not enabled"
        )
    
    if current_user.auth_provider != "ldap":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not an LDAP user"
        )
    
    # Get user info from LDAP
    ldap_info = await ldap_service.get_user_info(current_user.email)
    if not ldap_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in LDAP directory"
        )
    
    # Sync user data
    await sync_user_from_ldap(current_user, ldap_info)
    
    # Log activity
    access_method, device_id, session_id, _, _ = await get_access_info_direct(
        request, db
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        action_type=ActionType.USER_UPDATE.value,
        resource_type=ResourceType.USER,
        resource_id=current_user.id,
        device_id=device_id,
        session_id=session_id,
        access_method=access_method,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={"source": "ldap_sync"}
    )
    
    await db.commit()
    
    return {
        "message": "User synchronized from LDAP",
        "updated_fields": ["name", "ldap_dn", "external_id"]
    }


@router.get("/ldap/search")
async def search_ldap_users(
    query: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Search for users in LDAP directory (admin only)"""
    if not ldap_service.ldap_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LDAP authentication is not enabled"
        )
    
    if len(query) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must be at least 3 characters"
        )
    
    # Search LDAP
    ldap_users = await ldap_service.search_users(query)
    
    # Check which users already exist
    emails = [user.email for user in ldap_users]
    if emails:
        result = await db.execute(
            select(User.email).where(User.email.in_(emails))
        )
        existing_emails = {row[0] for row in result}
    else:
        existing_emails = set()
    
    # Format response
    return [
        {
            "uid": user.uid,
            "email": user.email,
            "name": user.name,
            "dn": user.dn,
            "exists": user.email in existing_emails
        }
        for user in ldap_users
    ]