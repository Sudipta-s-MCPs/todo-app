# OAuth Integration for Claude Desktop

**Last Updated**: 2025-07-03 22:10:00 PST

## Overview

Smart-ToDo now supports OAuth 2.0 authentication for Claude Desktop's native remote MCP integration. This allows Claude Desktop users to connect to the Smart-ToDo MCP server using the built-in Integrations feature without needing mcp-remote or additional proxy tools.

## Architecture

The OAuth integration works alongside the existing authentication systems:
- **API Keys**: For third-party REST API applications
- **MCP Agents**: For MCP clients (Claude Code, VS Code)
- **OAuth Tokens**: For Claude Desktop integration

OAuth tokens are linked to MCP agents, maintaining clear separation between app access and MCP access.

## Prerequisites

- Claude Desktop Pro, Max, Teams, or Enterprise account
- Smart-ToDo backend running with OAuth support
- Admin access to create OAuth clients

## OAuth Flow

Smart-ToDo implements the OAuth 2.0 authorization code flow with PKCE (Proof Key for Code Exchange) support:

1. **Authorization Request**: Claude Desktop opens browser to `/api/v1/oauth/authorize`
2. **User Login**: User authenticates with Smart-ToDo credentials
3. **Authorization Grant**: User approves access for Claude Desktop
4. **Authorization Code**: Smart-ToDo redirects back with authorization code
5. **Token Exchange**: Claude Desktop exchanges code for access token
6. **MCP Access**: Access token is used for MCP server authentication

## Admin Setup

### 1. Create OAuth Client

As an admin, create an OAuth client for Claude Desktop integration:

```bash
curl -X POST http://localhost:8000/api/v1/admin/oauth/clients \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Claude Desktop Integration",
    "client_type": "public",
    "redirect_uris": [
      "http://localhost:*",
      "claude://oauth/callback"
    ],
    "allowed_scopes": ["read", "write"]
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "client_id": "Ek1n3BqVv8G5xDqF2mNcPr7wZa9yLtS4",
  "client_name": "Claude Desktop Integration",
  "client_type": "public",
  "redirect_uris": ["http://localhost:*", "claude://oauth/callback"],
  "allowed_scopes": ["read", "write"],
  "registration_access_token": "rat_AbCdEf123456...",
  "created_at": "2025-07-03T21:30:00.000Z"
}
```

### 2. Dynamic Client Registration

Alternatively, Claude Desktop can dynamically register itself:

```bash
curl -X POST http://localhost:8000/api/v1/oauth/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Claude Desktop - John's MacBook",
    "client_type": "public",
    "redirect_uris": ["claude://oauth/callback"],
    "scopes": ["read", "write"]
  }'
```

## User Setup

### For Claude Desktop Users

1. **Open Claude Desktop Settings**
   - Click on your profile icon
   - Select "Settings"
   - Navigate to "Integrations"

2. **Add Remote MCP Server**
   - Click "Add Integration"
   - Select "Remote MCP Server"
   - Enter the following details:
     - **Server URL**: `http://localhost:5485/mcp`
     - **OAuth Authorization URL**: `http://localhost:8000/api/v1/auth/oauth/authorize`
     - **OAuth Token URL**: `http://localhost:8000/api/v1/auth/oauth/token`
     - **Client ID**: (provided by admin or from dynamic registration)

3. **Authenticate**
   - Click "Connect"
   - You'll be redirected to Smart-ToDo login page
   - Enter your credentials
   - Approve access for Claude Desktop
   - You'll be redirected back to Claude Desktop

4. **Verify Connection**
   - The integration should show as "Connected"
   - Smart-ToDo tools will appear in Claude's tool list

## OAuth Endpoints

### Authorization Endpoint
```
GET /api/v1/auth/oauth/authorize
```

Parameters:
- `response_type=code` (required)
- `client_id` (required)
- `redirect_uri` (required)
- `state` (recommended)
- `scope` (optional)
- `code_challenge` (required for PKCE)
- `code_challenge_method=S256` (required for PKCE)

### Token Endpoint
```
POST /api/v1/auth/oauth/token
```

Form parameters:
- `grant_type=authorization_code` or `refresh_token`
- `code` (for authorization_code grant)
- `redirect_uri` (for authorization_code grant)
- `client_id` (required)
- `code_verifier` (required for PKCE)
- `refresh_token` (for refresh_token grant)

### Token Revocation
```
POST /api/v1/auth/oauth/revoke
```

Form parameters:
- `token` (access or refresh token)
- `token_type_hint` (optional: access_token or refresh_token)
- `client_id` (required)

## Security Features

1. **PKCE Support**: Prevents authorization code interception attacks
2. **Dynamic Redirect URIs**: Supports Claude Desktop's dynamic localhost ports
3. **Token Expiration**: Access tokens expire in 1 hour, refresh tokens in 30 days
4. **Secure Storage**: Tokens are hashed before storage
5. **Revocation**: Tokens can be revoked by users or admins

## Admin Management

### View OAuth Clients
```bash
curl http://localhost:8000/api/v1/admin/oauth/clients \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Update OAuth Client
```bash
curl -X PATCH http://localhost:8000/api/v1/admin/oauth/clients/{client_id} \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "redirect_uris": ["claude://oauth/callback", "http://localhost:*"],
    "is_active": true
  }'
```

### View Active Tokens
```bash
curl http://localhost:8000/api/v1/admin/oauth/tokens \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Revoke Token
```bash
curl -X POST http://localhost:8000/api/v1/admin/oauth/tokens/{token_id}/revoke \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Troubleshooting

### "Invalid client" Error
- Verify the client_id is correct
- Check if the OAuth client is active
- Ensure redirect_uri matches registered URIs

### "Invalid redirect URI" Error
- Check if the redirect URI is in the client's allowed list
- For localhost, ensure wildcard pattern is configured

### "Authorization code expired"
- Authorization codes expire in 10 minutes
- Request a new authorization code

### Token Expired
- Access tokens expire in 1 hour
- Use refresh token to get new access token
- Refresh tokens expire in 30 days

### PKCE Verification Failed
- Ensure code_verifier matches code_challenge
- Use S256 method (SHA256 hash)
- Verifier must be 43-128 characters

## MCP Server OAuth Support

The MCP server supports dual authentication methods:

### 1. API Key Authentication (Default)
```
X-API-Key: {api_key}
X-Device-ID: {device_id}
X-Device-Name: {device_name}
```

### 2. OAuth Token Authentication (Claude Desktop)
```
Authorization: Bearer {oauth_access_token}
```

The MCP server automatically:
- Detects OAuth tokens in the Authorization header
- Validates tokens with the backend API
- Caches validation results for performance
- Falls back to API key authentication if no OAuth token

OAuth tokens are linked to:
- User account
- MCP agent (created automatically)
- Access permissions

## Migration from API Keys

Existing API key users can migrate to OAuth:

1. Admin creates OAuth client for the user
2. User authenticates via OAuth flow
3. OAuth token is linked to existing MCP agent
4. API key can be revoked (optional)

## Best Practices

1. **Client Types**:
   - Use "public" for Claude Desktop (no client secret)
   - Use "confidential" for server-to-server integrations

2. **Redirect URIs**:
   - Use exact URIs when possible
   - Use wildcards only for dynamic ports
   - Always use HTTPS in production

3. **Scopes**:
   - Limit scopes to minimum required
   - Standard scopes: read, write
   - Custom scopes can be added

4. **Token Management**:
   - Implement token refresh before expiration
   - Revoke tokens when no longer needed
   - Monitor token usage in admin panel

## API Reference

For detailed API documentation, see:
- [OAuth Endpoints API](./api/oauth.md)
- [Admin OAuth Management API](./api/admin-oauth.md)

## Support

For issues with OAuth integration:
1. Check Smart-ToDo logs: `docker-compose logs backend`
2. Verify OAuth client configuration
3. Test with OAuth debugging tools
4. Contact support with request/response details