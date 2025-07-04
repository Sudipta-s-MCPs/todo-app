# MCP Client Setup Guide

**Last Updated**: 2025-07-03 20:30:00 PST

## Overview

This guide helps you set up various MCP clients to connect to the Smart-ToDo MCP server.

## Prerequisites

- Smart-ToDo MCP server running on port 5485
- Node.js v16 or higher (required for mcp-remote proxy)

## Client Configurations

### Claude Code

Claude Code supports HTTP transport directly. Use the following command:

```bash
claude mcp add --transport http smart-todo http://localhost:5485/mcp \
  --header "X-API-Key: YOUR_API_KEY" \
  --header "X-Device-ID: YOUR_DEVICE_ID" \
  --header "X-Device-Name: YOUR_DEVICE_NAME" \
  --header "X-User-ID: YOUR_USER_ID"
```

### Claude Desktop

**Great News!** Claude Desktop now has native support for remote MCP servers (HTTP-based). You no longer need mcp-remote or Node.js!

#### Native Remote MCP Support (Recommended)

Available for Pro, Max, Teams, and Enterprise users:

**Option 1: OAuth Authentication (Preferred)**
See [OAuth Integration for Claude Desktop](./OAUTH_CLAUDE_DESKTOP_INTEGRATION.md) for detailed setup instructions.

**Option 2: API Key Authentication**
1. Open Claude Desktop
2. Go to **Settings > Integrations**
3. Add a new remote MCP server:
   - **Endpoint URL**: `http://localhost:5485/mcp`
   - **Authentication**: Configure headers as provided during agent registration

The authentication headers you'll need:
- `X-API-Key`: Your API key
- `X-Device-ID`: Your device ID
- `X-Device-Name`: Your device name
- `X-User-ID`: Your user ID

#### Legacy Configuration (If native support is not available)

For users without access to native remote MCP support, you can still use the manual configuration, but be aware of Node.js compatibility issues with mcp-remote.

### VS Code

Similar to Claude Desktop, VS Code requires mcp-remote proxy:

```json
{
  "mcp.servers": {
    "smart-todo": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:5485/mcp"],
      "environment": {
        "TODO_API_KEY": "YOUR_API_KEY",
        "TODO_USER_ID": "YOUR_USER_ID",
        "TODO_DEVICE_ID": "YOUR_DEVICE_ID",
        "TODO_DEVICE_NAME": "YOUR_DEVICE_NAME"
      }
    }
  }
}
```

## Troubleshooting

### "SyntaxError: The requested module 'node:fs/promises' does not provide an export named 'constants'"

This error occurs when using Node.js v14 or lower. The mcp-remote package requires Node.js v16+.

**Solution**: Update to Node.js v16 or higher.

### "No valid session ID provided" Error

This error can occur if the MCP server restarts or if the session expires. 

**Solution**: Restart your MCP client to establish a new session.

### Connection Refused

Ensure the MCP server is running:
```bash
docker-compose logs mcp-server
```

The server should be listening on `http://0.0.0.0:5485/mcp/`

## Getting Your Credentials

1. Register an MCP agent through the admin panel at http://localhost:5483
2. Navigate to Settings > MCP Agents
3. Click "Register New Agent"
4. Save the provided API key and configuration details

## Testing Your Connection

After configuration, verify the connection:

**Claude Code**:
```bash
claude mcp list
```

**Claude Desktop**: 
- Restart Claude Desktop
- Check if "smart-todo" appears in available tools

**In your MCP client**:
- Try using the `list_tasks` tool
- Or use `smart_todo_manager` with a message like "Show me my tasks"