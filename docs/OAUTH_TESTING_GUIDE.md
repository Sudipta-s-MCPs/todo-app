# OAuth Testing Guide for Claude Desktop Integration

**Last Updated**: 2025-07-03 22:30:00 PST

## Prerequisites

- Smart-ToDo backend running on port 5482
- MCP server running on port 5485
- Admin account for creating OAuth clients
- Claude Desktop Pro/Max/Teams/Enterprise account

## Testing Steps

### 1. Verify Services are Running

```bash
# Check backend and MCP server status
docker-compose ps

# Verify OAuth endpoints
python verify_oauth_endpoints.py
```

### 2. Create OAuth Client (Admin Panel)

#### Option A: Using the Test Script

```bash
# Run the comprehensive test suite
python test_oauth_flow.py
```

This will:
1. Prompt for admin credentials
2. Create an OAuth client
3. Walk you through the authorization flow
4. Test token exchange
5. Verify API and MCP server access
6. Test token refresh and revocation

#### Option B: Manual Creation via Admin Panel

1. Login to admin panel: http://localhost:3001
2. Navigate to OAuth Clients section
3. Create new client with:
   - Name: "Claude Desktop Integration"
   - Type: "public"
   - Redirect URIs: 
     - `http://localhost:*`
     - `claude://oauth/callback`
   - Scopes: `read`, `write`

### 3. Test OAuth Flow Manually

#### Step 1: Build Authorization URL

```
http://localhost:5482/api/v1/auth/oauth/authorize?
  response_type=code&
  client_id=YOUR_CLIENT_ID&
  redirect_uri=http://localhost:5482/api/v1/auth/oauth/callback&
  scope=read%20write&
  state=random_state&
  code_challenge=YOUR_CODE_CHALLENGE&
  code_challenge_method=S256
```

#### Step 3: Complete Authorization

1. Open the authorization URL in your browser
2. Login with your Smart-ToDo credentials
3. Click "Allow Access"
4. Copy the authorization code from the callback page

#### Step 4: Exchange Code for Token

```bash
curl -X POST http://localhost:5482/api/v1/auth/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=YOUR_AUTH_CODE" \
  -d "redirect_uri=http://localhost:5482/api/v1/auth/oauth/callback" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "code_verifier=YOUR_CODE_VERIFIER"
```

#### Step 5: Test API Access

```bash
# Test with OAuth token
curl http://localhost:5482/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Test MCP server
curl -X POST http://localhost:5485/mcp \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": "test-1"
  }'
```

### 4. Configure Claude Desktop

1. Open Claude Desktop
2. Go to Settings → Integrations
3. Add Remote MCP Server:
   - **Server URL**: `http://localhost:5485/mcp`
   - **OAuth Authorization URL**: `http://localhost:5482/api/v1/auth/oauth/authorize`
   - **OAuth Token URL**: `http://localhost:5482/api/v1/auth/oauth/token`
   - **Client ID**: Your OAuth client ID

4. Click "Connect"
5. Complete the authorization flow
6. Verify Smart-ToDo tools appear in Claude

## Troubleshooting

### Connection Refused

- Ensure services are running: `docker-compose ps`
- Check logs: `docker-compose logs -f backend mcp-server`

### Invalid Client Error

- Verify client_id is correct
- Check if OAuth client is active in admin panel
- Ensure redirect_uri matches registered URIs

### PKCE Verification Failed

- Ensure code_verifier matches the one used to generate code_challenge
- Use SHA256 method for code challenge generation
- Verifier must be 43-128 characters

### Token Not Working with MCP Server

- Check MCP server logs: `docker-compose logs -f mcp-server`
- Verify OAuth token validation is working
- Ensure token hasn't expired (1 hour lifetime)

### Claude Desktop Not Showing Tools

- Refresh Claude Desktop
- Check if MCP agent was created for the OAuth client
- Verify MCP server is accessible from Claude Desktop

## Test Data

### Sample PKCE Values

```python
# Generate in Python
import secrets
import hashlib
import base64

code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode('utf-8')).digest()
).decode('utf-8').rstrip('=')

print(f"Code Verifier: {code_verifier}")
print(f"Code Challenge: {code_challenge}")
```

### Sample Authorization URL

```
http://localhost:5482/api/v1/auth/oauth/authorize?
response_type=code&
client_id=Ek1n3BqVv8G5xDqF2mNcPr7wZa9yLtS4&
redirect_uri=http://localhost:5482/api/v1/auth/oauth/callback&
scope=read%20write&
state=test123&
code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&
code_challenge_method=S256
```

## Security Notes

1. **Development Only**: These localhost URLs are for development testing only
2. **HTTPS in Production**: Always use HTTPS in production
3. **Client Secrets**: Never expose client secrets for confidential clients
4. **Token Storage**: OAuth tokens are hashed in the database
5. **Expiration**: Access tokens expire in 1 hour, refresh tokens in 30 days

## Testing Steps Summary

1. Create OAuth client: `docker-compose exec backend python scripts/create_oauth_client.py`
2. Run test script: `python test_oauth_flow.py`
3. Or manually test by opening the authorization URL in browser
4. Configure Claude Desktop with:
   - Server URL: `http://localhost:5485/mcp`
   - OAuth URLs as shown above
   - Client ID from the created OAuth client

## Next Steps

After successful testing:

1. Monitor OAuth client usage in admin panel
2. Review activity logs for OAuth authentications
3. Test token refresh before expiration
4. Implement proper error handling in your integration
5. Consider rate limiting for production use