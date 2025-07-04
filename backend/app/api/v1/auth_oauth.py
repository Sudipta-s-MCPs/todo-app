"""
OAuth 2.0 flow endpoints for Claude Desktop and other OAuth clients
Created: 2025-07-03 21:45:00 PST
"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User, MCPAgent, DeviceType, AccessMethod
from app.models.oauth import OAuthClient, OAuthAuthorizationCode, OAuthToken
from app.models.activity import ActivityLog, ActionType, ResourceType
from app.config import settings
from app.services.activity import log_activity
from app.middleware import rate_limit
from app.utils.logging import security_logger
from app.utils.security import get_password_hash, verify_password
from app.api.deps import get_current_user_optional

router = APIRouter()


class OAuthTokenRequest(BaseModel):
    """OAuth token request"""
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: str
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class OAuthTokenResponse(BaseModel):
    """OAuth token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


def generate_authorization_code() -> str:
    """Generate secure authorization code"""
    return secrets.token_urlsafe(32)


def verify_code_challenge(verifier: str, challenge: str, method: str = "S256") -> bool:
    """Verify PKCE code challenge"""
    if method == "plain":
        return verifier == challenge
    elif method == "S256":
        # SHA256(verifier) = challenge
        verifier_hash = hashlib.sha256(verifier.encode()).digest()
        verifier_challenge = base64.urlsafe_b64encode(verifier_hash).decode().rstrip("=")
        return verifier_challenge == challenge
    return False


@router.get("/oauth/authorize")
async def authorize(
    request: Request,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: Optional[str] = None,
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = "S256",
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth 2.0 authorization endpoint
    """
    # Validate response_type
    if response_type != "code":
        return HTMLResponse(
            content=f"<h1>Error</h1><p>Unsupported response type: {response_type}</p>",
            status_code=400
        )
    
    # Find OAuth client
    result = await db.execute(
        select(OAuthClient).where(
            OAuthClient.client_id == client_id,
            OAuthClient.is_active == True
        )
    )
    oauth_client = result.scalar_one_or_none()
    
    if not oauth_client:
        return HTMLResponse(
            content="<h1>Error</h1><p>Invalid client</p>",
            status_code=400
        )
    
    # Verify redirect URI
    if not oauth_client.verify_redirect_uri(redirect_uri):
        return HTMLResponse(
            content="<h1>Error</h1><p>Invalid redirect URI</p>",
            status_code=400
        )
    
    # Store authorization request in session (in production, use secure session storage)
    # For now, we'll render a simple login form
    login_form = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Smart-ToDo Authorization</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; margin-bottom: 10px; }}
            .client-info {{ background: #f0f0f0; padding: 15px; border-radius: 4px; margin-bottom: 20px; }}
            .client-name {{ font-weight: bold; color: #0066cc; }}
            form {{ margin-top: 20px; }}
            input {{ width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
            button {{ background: #0066cc; color: white; padding: 12px 20px; margin: 8px 0; border: none; border-radius: 4px; cursor: pointer; width: 48%; }}
            button:hover {{ background: #0052a3; }}
            button[name="action"][value="deny"] {{ background: #666; }}
            button[name="action"][value="deny"]:hover {{ background: #555; }}
            .button-group {{ display: flex; justify-content: space-between; margin-top: 20px; }}
            .scopes {{ margin: 15px 0; }}
            .scope-item {{ padding: 5px 0; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Authorization Request</h1>
            <div class="client-info">
                <span class="client-name">{oauth_client.client_name}</span> is requesting access to your Smart-ToDo account.
            </div>
            
            {f'<div class="scopes"><strong>Requested permissions:</strong><div class="scope-item">• {scope or "Read and write access"}</div></div>' if scope else ''}
            
            <form method="post" action="/api/v1/auth/oauth/authorize">
                <input type="hidden" name="client_id" value="{client_id}">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="response_type" value="{response_type}">
                <input type="hidden" name="scope" value="{scope or ''}">
                <input type="hidden" name="state" value="{state or ''}">
                <input type="hidden" name="code_challenge" value="{code_challenge or ''}">
                <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
                
                <input type="email" name="email" placeholder="Email" required autofocus>
                <input type="password" name="password" placeholder="Password" required>
                
                <div class="button-group">
                    <button type="submit" name="action" value="deny">Deny</button>
                    <button type="submit" name="action" value="allow">Allow Access</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=login_form)


@router.post("/oauth/authorize")
async def authorize_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    action: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    response_type: str = Form(...),
    scope: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    code_challenge: Optional[str] = Form(None),
    code_challenge_method: str = Form("S256"),
    db: AsyncSession = Depends(get_db)
):
    """
    Process OAuth authorization form submission
    """
    # Check if user denied access
    if action == "deny":
        params = {"error": "access_denied"}
        if state:
            params["state"] = state
        return RedirectResponse(url=f"{redirect_uri}?{urlencode(params)}")
    
    # Verify user credentials
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.password_hash):
        # Return to login form with error
        return HTMLResponse(
            content="""
            <html>
            <head>
                <title>Authorization Failed</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
                    .error { color: #d32f2f; margin-bottom: 20px; }
                    a { color: #0066cc; text-decoration: none; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Authorization Failed</h1>
                    <p class="error">Invalid email or password.</p>
                    <p><a href="javascript:history.back()">Go back and try again</a></p>
                </div>
            </body>
            </html>
            """,
            status_code=401
        )
    
    # Check if user is approved
    if user.approval_status != "approved":
        return HTMLResponse(
            content="""
            <html>
            <head>
                <title>Account Pending</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
                    .warning { color: #f57c00; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Account Pending Approval</h1>
                    <p class="warning">Your account is pending approval. Please contact an administrator.</p>
                </div>
            </body>
            </html>
            """,
            status_code=403
        )
    
    # Find OAuth client
    result = await db.execute(
        select(OAuthClient).where(
            OAuthClient.client_id == client_id,
            OAuthClient.is_active == True
        )
    )
    oauth_client = result.scalar_one_or_none()
    
    if not oauth_client:
        return HTMLResponse(
            content="<h1>Error</h1><p>Invalid client</p>",
            status_code=400
        )
    
    # Generate authorization code
    auth_code = generate_authorization_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Store authorization code
    oauth_code = OAuthAuthorizationCode(
        code=auth_code,
        client_id=oauth_client.id,
        user_id=user.id,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method if code_challenge else None,
        expires_at=expires_at
    )
    
    db.add(oauth_code)
    await db.commit()
    
    # Log activity
    await log_activity(
        db=db,
        user_id=user.id,
        action_type=ActionType.LOGIN.value,
        resource_type=ResourceType.MCP_AGENT,
        resource_id=oauth_client.id,
        access_method=AccessMethod.OAUTH,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        details={"client_name": oauth_client.client_name, "action": "oauth_authorize"}
    )
    
    # Redirect back to client with authorization code
    params = {"code": auth_code}
    if state:
        params["state"] = state
    
    return RedirectResponse(url=f"{redirect_uri}?{urlencode(params)}")


@router.post("/oauth/token", response_model=OAuthTokenResponse)
@rate_limit(requests_per_minute=20)
async def token(
    request: Request,
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth 2.0 token endpoint
    """
    # Find OAuth client
    result = await db.execute(
        select(OAuthClient).where(
            OAuthClient.client_id == client_id,
            OAuthClient.is_active == True
        )
    )
    oauth_client = result.scalar_one_or_none()
    
    if not oauth_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client"
        )
    
    # Verify client secret for confidential clients
    if oauth_client.client_type == "confidential":
        if not client_secret or not verify_password(client_secret, oauth_client.client_secret_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client credentials"
            )
    
    if grant_type == "authorization_code":
        if not code or not redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters"
            )
        
        # Find authorization code
        result = await db.execute(
            select(OAuthAuthorizationCode).where(
                OAuthAuthorizationCode.code == code,
                OAuthAuthorizationCode.client_id == oauth_client.id,
                OAuthAuthorizationCode.redirect_uri == redirect_uri
            )
        )
        auth_code = result.scalar_one_or_none()
        
        if not auth_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid authorization code"
            )
        
        # Check if code is expired or used
        if auth_code.is_expired or auth_code.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code expired or already used"
            )
        
        # Verify PKCE if present
        if auth_code.code_challenge:
            if not code_verifier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Code verifier required"
                )
            
            if not verify_code_challenge(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid code verifier"
                )
        
        # Mark code as used
        auth_code.use()
        
        # Generate tokens
        tokens = OAuthToken.generate_tokens()
        access_token_expires = datetime.utcnow() + timedelta(hours=1)
        refresh_token_expires = datetime.utcnow() + timedelta(days=30)
        
        # Create or find MCP agent for this OAuth client
        result = await db.execute(
            select(MCPAgent).where(
                MCPAgent.user_id == auth_code.user_id,
                MCPAgent.agent_name == f"Claude Desktop ({oauth_client.client_name})"
            )
        )
        mcp_agent = result.scalar_one_or_none()
        
        if not mcp_agent:
            # Create new MCP agent
            mcp_agent = MCPAgent(
                user_id=auth_code.user_id,
                agent_identifier=f"oauth_{oauth_client.client_id[:8]}_{secrets.token_hex(4)}",
                agent_name=f"Claude Desktop ({oauth_client.client_name})",
                auth_method="oauth",  # Mark as OAuth authenticated
                capabilities=["task_management", "list_management", "search", "smart_todo_manager"],
                permissions=["tasks:read", "tasks:write", "lists:read", "lists:write", "workspaces:read"],
                is_active=True
            )
            db.add(mcp_agent)
            await db.flush()
        
        # Create OAuth token
        oauth_token = OAuthToken(
            access_token_hash=get_password_hash(tokens["access_token"]),
            refresh_token_hash=get_password_hash(tokens["refresh_token"]),
            client_id=oauth_client.id,
            user_id=auth_code.user_id,
            scope=auth_code.scope,
            access_token_expires_at=access_token_expires,
            refresh_token_expires_at=refresh_token_expires,
            device_id=mcp_agent.identifier,
            device_name=mcp_agent.name,
            mcp_agent_id=mcp_agent.id
        )
        
        db.add(oauth_token)
        await db.commit()
        
        response = OAuthTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=3600,
            scope=auth_code.scope
        )
        
        return response
    
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )
        
        # Find OAuth token by refresh token
        result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.client_id == oauth_client.id
            )
        )
        all_tokens = result.scalars().all()
        
        oauth_token = None
        for token in all_tokens:
            if verify_password(refresh_token, token.refresh_token_hash):
                oauth_token = token
                break
        
        if not oauth_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token is expired or revoked
        if oauth_token.is_refresh_token_expired or oauth_token.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token expired or revoked"
            )
        
        # Generate new access token
        new_access_token = secrets.token_urlsafe(32)
        oauth_token.access_token_hash = get_password_hash(new_access_token)
        oauth_token.access_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        oauth_token.update_last_used()
        
        await db.commit()
        
        response = OAuthTokenResponse(
            access_token=new_access_token,
            expires_in=3600,
            scope=oauth_token.scope
        )
        
        return response
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported grant type: {grant_type}"
        )


@router.post("/oauth/revoke")
@rate_limit(requests_per_minute=10)
async def revoke_token(
    request: Request,
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth 2.0 token revocation endpoint
    """
    # Find OAuth client
    result = await db.execute(
        select(OAuthClient).where(
            OAuthClient.client_id == client_id,
            OAuthClient.is_active == True
        )
    )
    oauth_client = result.scalar_one_or_none()
    
    if not oauth_client:
        # Per RFC 7009, return success even if client is invalid
        return Response(status_code=200)
    
    # Verify client secret for confidential clients
    if oauth_client.client_type == "confidential":
        if not client_secret or not verify_password(client_secret, oauth_client.client_secret_hash):
            # Per RFC 7009, return success even if authentication fails
            return Response(status_code=200)
    
    # Try to find token
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.client_id == oauth_client.id
        )
    )
    all_tokens = result.scalars().all()
    
    oauth_token = None
    for t in all_tokens:
        if (verify_password(token, t.access_token_hash) or 
            (t.refresh_token_hash and verify_password(token, t.refresh_token_hash))):
            oauth_token = t
            break
    
    # Revoke token if found
    if oauth_token and not oauth_token.is_revoked:
        oauth_token.revoke()
        await db.commit()
        
        # Log activity
        await log_activity(
            db=db,
            user_id=oauth_token.user_id,
            action_type=ActionType.LOGOUT.value,
            resource_type=ResourceType.MCP_AGENT,
            resource_id=oauth_client.id,
            access_method=AccessMethod.OAUTH,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            details={"action": "token_revoked"}
        )
    
    # Always return success per RFC 7009
    return Response(status_code=200)


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """
    OAuth callback endpoint for Claude Desktop
    
    This endpoint handles the OAuth callback after authorization.
    Claude Desktop will be configured to redirect here.
    """
    if error:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Failed</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}
                    .container {{ max-width: 500px; margin: 0 auto; }}
                    .error {{ color: #d32f2f; }}
                    .message {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="error">Authorization Failed</h1>
                    <div class="message">
                        <p><strong>{error}</strong></p>
                        <p>{error_description or 'Unknown error occurred'}</p>
                    </div>
                    <p>You can close this window and return to Claude Desktop.</p>
                </div>
            </body>
            </html>
            """,
            status_code=400
        )
    
    if not code:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Missing Authorization Code</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
                    .container { max-width: 500px; margin: 0 auto; }
                    .error { color: #d32f2f; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="error">Missing Authorization Code</h1>
                    <p>No authorization code was provided.</p>
                    <p>You can close this window and return to Claude Desktop.</p>
                </div>
            </body>
            </html>
            """,
            status_code=400
        )
    
    # Success page with instructions
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authorization Successful</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; background: #f5f5f5; }}
                .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .success {{ color: #4caf50; }}
                .code {{ background: #f5f5f5; padding: 15px; border-radius: 4px; font-family: monospace; word-break: break-all; margin: 20px 0; }}
                .icon {{ font-size: 48px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✅</div>
                <h1 class="success">Authorization Successful!</h1>
                <p>You have successfully authorized Claude Desktop to access your Smart-ToDo account.</p>
                
                <div class="code">
                    <strong>Authorization Code:</strong><br>
                    {code}
                </div>
                
                <p>Claude Desktop should automatically complete the setup.</p>
                <p>If not, you can copy the authorization code above.</p>
                <p style="margin-top: 30px; color: #666;">You can close this window.</p>
            </div>
            
            <script>
                // Attempt to redirect to Claude Desktop custom URL scheme
                // This may or may not work depending on browser and OS
                setTimeout(function() {{
                    window.location.href = 'claude://oauth/callback?code={code}&state={state or ""}';
                }}, 1000);
            </script>
        </body>
        </html>
        """
    )