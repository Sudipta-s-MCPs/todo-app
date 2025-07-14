# Official MCP Setup Guide for Smart-ToDo

**Last Updated**: 2025-07-14  
**MCP Implementation**: Official MCP Library v1.9.4+

## Overview

Smart-ToDo now uses the official MCP (Model Context Protocol) library, providing perfect compatibility with Claude Desktop and other MCP clients. This guide covers the complete setup process.

## Prerequisites

- Python 3.8 or higher
- Smart-ToDo backend running (default: http://localhost:5482)
- API credentials (obtained via setup script)

## Installation

### 1. Install Dependencies

The official MCP library is included in the main requirements:

```bash
cd backend
pip install -r requirements.txt
```

Key dependencies:
- `mcp>=1.9.4` - Official MCP library
- `httpx>=0.24.0` - HTTP client for API calls
- `anyio>=3.6.0` - Async support

### 2. Get API Credentials

Register an MCP agent to obtain credentials:

```bash
cd backend
python mcp_server/setup_mcp.py
```

This will provide:
- **API Key**: Authentication token
- **User ID**: Your user identifier
- **Device ID**: Unique device identifier
- **Device Name**: Human-readable device name

Save these credentials securely - you'll need them for configuration.

## Configuration Options

### Option 1: Direct stdio Connection (Recommended)

The cleanest setup with no schema issues, perfect for Claude Desktop.

#### Claude Desktop Configuration

Edit your Claude Desktop config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Add the following configuration:

```json
{
  "mcpServers": {
    "Smart ToDo": {
      "command": "/usr/local/bin/python3",
      "args": [
        "/path/to/backend/mcp_server/server_official.py"
      ],
      "env": {
        "TODO_API_ENDPOINT": "http://localhost:5482/api/v1",
        "TODO_API_KEY": "your-api-key-here",
        "TODO_USER_ID": "your-user-id-here",
        "TODO_DEVICE_ID": "your-device-id-here",
        "TODO_DEVICE_NAME": "Claude Desktop",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

#### Claude Code Configuration

For Claude Code, use:

```json
{
  "Smart ToDo": {
    "type": "stdio",
    "command": "/usr/local/bin/python3",
    "args": ["/path/to/backend/mcp_server/server_official.py"],
    "env": {
      "TODO_API_ENDPOINT": "http://localhost:5482/api/v1",
      "TODO_API_KEY": "your-api-key-here",
      "TODO_USER_ID": "your-user-id-here",
      "TODO_DEVICE_ID": "your-device-id-here",
      "TODO_DEVICE_NAME": "Claude Code"
    }
  }
}
```

### Option 2: HTTP Bridge Connection

Use this option if you:
- Run Smart-ToDo in Docker
- Prefer HTTP transport
- Need remote access

#### Step 1: Run the HTTP Server

The FastMCP server still works for HTTP transport:

```bash
cd backend
python mcp_server/server.py  # Runs on port 5485
```

Or with Docker:

```bash
docker-compose up mcp-server
```

#### Step 2: Configure Claude Desktop

Use the stdio bridge client:

```json
{
  "mcpServers": {
    "Smart ToDo": {
      "command": "/usr/local/bin/python3",
      "args": [
        "/path/to/backend/mcp_server/client_wrapper.py"
      ],
      "env": {
        "TODO_API_KEY": "your-api-key-here",
        "TODO_USER_ID": "your-user-id-here",
        "TODO_DEVICE_ID": "your-device-id-here",
        "TODO_DEVICE_NAME": "Claude Desktop",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

## Available Tools

The MCP server provides 11 tools for task management:

### Core Task Operations
- `create_task` - Create new tasks with duplicate detection
- `smart_create_task` - Create tasks using natural language
- `list_tasks` - List tasks with filters
- `update_task` - Update task properties
- `complete_task` - Mark tasks as completed
- `delete_task` - Delete (archive) tasks
- `search_tasks` - Search tasks by text
- `get_task` - Get detailed task information

### Organization Tools
- `list_workspaces` - List all workspaces
- `list_lists` - List all lists
- `get_stats` - Get task statistics

## Testing Your Setup

### 1. Test the Server Directly

```bash
# Test initialization
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0.0"}}, "id": 1}' | python3 server_official.py

# List available tools
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}' | python3 server_official.py
```

### 2. Test in Claude Desktop

After configuration, restart Claude Desktop and try:

```
"Can you list my tasks?"
"Create a task: Buy groceries tomorrow"
"Show me my workspaces"
```

## Troubleshooting

### "Module not found" Errors

Ensure all dependencies are installed:

```bash
pip install mcp httpx anyio jsonschema python-dateutil
```

### Authentication Errors

Verify your credentials:
- API key starts with `mcp_`
- All environment variables are set correctly
- The backend server is running

### Connection Issues

Check:
- Backend is accessible at the configured endpoint
- No firewall blocking connections
- Correct Python path in configuration

### Schema Validation Errors

If you see schema errors in Claude Desktop:
- Ensure you're using `server_official.py` (not the old FastMCP server)
- Verify you have the latest version of the official MCP library

## Advanced Configuration

### Custom API Endpoint

For production or remote deployments:

```json
"TODO_API_ENDPOINT": "https://todo-api.yourdomain.com/api/v1"
```

### Logging

Enable debug logging:

```json
"env": {
  ...
  "LOG_LEVEL": "DEBUG"
}
```

### Multiple Environments

Create separate configurations for different environments:

```json
{
  "mcpServers": {
    "Smart ToDo (Dev)": {
      // Development configuration
    },
    "Smart ToDo (Prod)": {
      // Production configuration
    }
  }
}
```

## Migration from FastMCP

If you're migrating from the old FastMCP implementation:

1. The new server is at `server_official.py`
2. Update your configuration to use the new path
3. All tools remain the same - no changes to your workflows
4. Enjoy better Claude Desktop compatibility!

## Benefits of Official MCP

- ✅ **No Schema Issues**: Clean JSON schemas without context parameters
- ✅ **Claude Desktop Compatible**: Works perfectly out of the box
- ✅ **Standards Compliant**: Official MCP protocol implementation
- ✅ **Better Performance**: Direct stdio connection
- ✅ **Future Proof**: Maintained by the MCP team

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the [MCP documentation](https://github.com/modelcontextprotocol/docs)
3. Open an issue in the Smart-ToDo repository

---

Happy task managing with Claude! 🎉