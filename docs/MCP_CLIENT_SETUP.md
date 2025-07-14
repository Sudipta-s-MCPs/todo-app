# MCP Client Setup Guide

**Last Updated**: 2025-07-14
**MCP Server**: Official MCP Library (replaced FastMCP)

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

**Two Configuration Options Available:**

#### Option 1: Direct stdio Connection (Recommended - No Schema Issues)

Use the official MCP server directly for the cleanest setup:

```json
{
  "Smart ToDo": {
    "command": "/usr/local/bin/python3",
    "args": [
      "/path/to/backend/mcp_server/server_official.py"
    ],
    "env": {
      "TODO_API_ENDPOINT": "http://localhost:5482/api/v1",
      "TODO_API_KEY": "your-api-key",
      "TODO_USER_ID": "your-user-id",
      "TODO_DEVICE_ID": "your-device-id",
      "TODO_DEVICE_NAME": "Claude Desktop",
      "PYTHONUNBUFFERED": "1"
    }
  }
}
```

#### Option 2: HTTP Bridge Connection (Docker-friendly)

If you prefer to keep using the HTTP bridge (especially with Docker deployments):

```json
{
  "Smart ToDo": {
    "command": "/usr/local/bin/python3",
    "args": [
      "/path/to/backend/mcp_server/client_wrapper.py"
    ],
    "env": {
      "TODO_API_KEY": "your-api-key",
      "TODO_USER_ID": "your-user-id",
      "TODO_DEVICE_ID": "your-device-id",
      "TODO_DEVICE_NAME": "Claude Desktop",
      "PYTHONUNBUFFERED": "1"
    }
  }
}
```

**Note**: Option 1 uses the new official MCP implementation which has perfect Claude Desktop compatibility with no schema issues.

### VS Code

Use the official MCP server directly:

```json
{
  "mcp.servers": {
    "smart-todo": {
      "command": "python3",
      "args": ["/path/to/backend/mcp_server/server_official.py"],
      "environment": {
        "TODO_API_ENDPOINT": "http://localhost:5482/api/v1",
        "TODO_API_KEY": "YOUR_API_KEY",
        "TODO_USER_ID": "YOUR_USER_ID",
        "TODO_DEVICE_ID": "YOUR_DEVICE_ID",
        "TODO_DEVICE_NAME": "VS Code"
      }
    }
  }
}
```

## Getting Your API Credentials

Run the setup script to register an MCP agent:

```bash
cd backend
python mcp_server/setup_mcp.py
```

This will provide you with:
- API Key (`TODO_API_KEY`)
- User ID (`TODO_USER_ID`)
- Device ID (`TODO_DEVICE_ID`)
- Device Name (`TODO_DEVICE_NAME`)

## Troubleshooting

### Schema Validation Errors in Claude Desktop

If using the old FastMCP server, switch to `server_official.py` which has clean schemas.

### Connection Issues

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