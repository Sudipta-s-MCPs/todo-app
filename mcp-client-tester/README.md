# MCP Client Tester

This directory contains the MCP (Model Context Protocol) client for testing the Smart-ToDo MCP server.

## Overview

The MCP client communicates with the Smart-ToDo MCP server using the Model Context Protocol over HTTP transport (Streamable HTTP). This is how AI assistants like Claude would interact with Smart-ToDo.

## MCP HTTP Client (`mcp_http_client.py`)

- **Purpose**: Tests MCP server functionality using the proper MCP protocol
- **Protocol**: MCP over HTTP (Streamable HTTP transport) - Protocol version 2025-03-26
- **Port**: 5485 (MCP server)
- **Endpoint**: `http://localhost:5485/mcp/`

### Usage

```bash
# Run interactive mode (full menu)
python mcp_http_client.py

# Run quick test (basic functionality)
python mcp_http_client.py --quick

# Run comprehensive test (full workflow)
python mcp_http_client.py --comprehensive

# Show help
python mcp_http_client.py --help
```

### Features

#### Core MCP Features
- **MCP Protocol Compliance**: Implements proper JSON-RPC 2.0 communication
- **Session Management**: Handles MCP session IDs
- **Tool Discovery**: Lists available MCP tools
- **Resource Access**: Read MCP resources (tasks://recent, tasks://upcoming)
- **Prompt Templates**: Access and use MCP prompts

#### Task Management Tools
- **Basic Operations**: Create, list, update, delete, complete tasks
- **List Management**: Create lists, move tasks between lists
- **Search**: Full-text search across tasks
- **Smart Filters**: Get upcoming tasks by date range

#### AI-Powered Features
- **Smart Todo Manager**: Natural language task management with multiple modes:
  - `auto`: AI decides the best action based on context
  - `create_task`: Force task creation from natural language
  - `chat`: General conversation without task creation
  - `suggest`: Get task suggestions without auto-creation
- **AI Integration**: Uses the same AI system as the frontend chat
- **Duplicate Detection**: AI-powered duplicate detection when creating tasks

#### Testing Capabilities
- **Interactive Menu**: User-friendly CLI with 15 different operations
- **Quick Test**: Tests 11 core MCP features in under 30 seconds
- **Comprehensive Test**: Full end-to-end workflow testing including AI features

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

## Available MCP Tools

The client can test all 11 MCP tools exposed by the server:

1. **create_task** - Create new tasks with duplicate detection
2. **list_tasks** - List tasks with optional filtering
3. **update_task** - Update task properties
4. **complete_task** - Mark tasks as completed
5. **delete_task** - Delete (archive) tasks
6. **search_tasks** - Search tasks by text query
7. **create_list** - Create new lists in workspaces
8. **get_lists** - Get all lists organized by workspace
9. **move_task** - Move tasks between lists
10. **get_upcoming_tasks** - Get tasks due in next N days
11. **smart_todo_manager** - AI-powered conversational task management

## Available MCP Resources

- **tasks://recent** - Recently modified tasks
- **tasks://upcoming** - Tasks due soon

## Available MCP Prompts

- **daily_planning_prompt** - Helps organize the day
- **project_breakdown_prompt** - Break projects into tasks
- **task_review_prompt** - Review and cleanup tasks

## Current Status

- ✅ All 11 MCP tools fully implemented and tested
- ✅ Resource reading (tasks://recent, tasks://upcoming)
- ✅ Prompt retrieval with parameter support
- ✅ AI integration with smart_todo_manager
- ✅ Streamable HTTP transport (protocol version 2025-03-26)
- ✅ Session management with MCP session IDs
- ✅ Comprehensive error handling and recovery

## Protocol Details

The MCP client implements:
- **Protocol Version**: 2025-03-26 (Streamable HTTP)
- **Transport**: HTTP with optional SSE streaming
- **Message Format**: JSON-RPC 2.0
- **Headers**: 
  - Content-Type: `application/json`
  - Accept: `application/json, text/event-stream`
  - Mcp-Session-Id: Session tracking header
- **Error Handling**: Graceful handling of both JSON and SSE responses