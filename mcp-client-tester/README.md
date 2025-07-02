# MCP Client Tester

This directory contains the MCP (Model Context Protocol) client for testing the Smart-ToDo MCP server.

## Overview

The MCP client communicates with the Smart-ToDo MCP server using the Model Context Protocol over HTTP transport (Streamable HTTP). This is how AI assistants like Claude would interact with Smart-ToDo.

## MCP HTTP Client (`mcp_http_client.py`)

- **Purpose**: Tests MCP server functionality using the proper MCP protocol
- **Protocol**: MCP over HTTP (Streamable HTTP transport)
- **Port**: 5485 (MCP server)
- **Endpoint**: `http://localhost:5485/mcp/`

### Usage

```bash
# Run interactive mode
python mcp_http_client.py

# Run quick test
python mcp_http_client.py --quick
```

### Features

- **MCP Protocol Compliance**: Implements proper JSON-RPC 2.0 communication
- **Session Management**: Handles MCP session IDs
- **Tool Discovery**: Lists available MCP tools
- **Task Operations**: Create, list, update, delete tasks via MCP protocol
- **Interactive Testing**: User-friendly CLI for exploring MCP functionality

### Authentication

The MCP client uses the registered MCP agent credentials:
- API Key: `sk_todo_dXUp4PpVrpoSHUaN28CQMKJXGuNJZs7vCiTcmxAX`
- Agent ID: `mcp_K0YxB7lyqgjOZLTv`

### Requirements

```bash
pip install httpx rich
```

## Difference from API Testing

For direct API testing, use the comprehensive test suite in `/test-client/` directory which includes:
- `test_api.py` - Core API endpoint tests
- `test_e2e_scenarios.py` - End-to-end scenario testing
- `test_frontend_features.py` - Frontend feature testing
- `test_websocket.py` - WebSocket functionality testing

This MCP client tester is specifically for testing the MCP protocol layer, not the direct REST API.

## Current Status

- ✅ MCP server initialization works
- ✅ Session management implemented
- ⚠️ Tool discovery has parameter validation issues (under investigation)

## Protocol Details

The MCP client implements:
- JSON-RPC 2.0 message format
- HTTP POST requests with SSE response support
- Proper Accept headers: `application/json, text/event-stream`
- Session ID tracking via `Mcp-Session-Id` header