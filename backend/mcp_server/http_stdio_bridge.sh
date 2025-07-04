#!/bin/bash
# HTTP to STDIO Bridge for Smart-ToDo MCP Server
# Created: 2025-07-03 20:42:00 PST

MCP_ENDPOINT="${MCP_ENDPOINT:-http://localhost:5485/mcp}"
SESSION_ID=""

# Function to send request and handle response
send_request() {
    local request="$1"
    local headers=""
    
    # Add session ID if we have one
    if [ -n "$SESSION_ID" ]; then
        headers="-H \"Mcp-Session-Id: $SESSION_ID\""
    fi
    
    # Send request with authentication headers
    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $TODO_API_KEY" \
        -H "X-Device-ID: $TODO_DEVICE_ID" \
        -H "X-Device-Name: $TODO_DEVICE_NAME" \
        -H "X-User-ID: $TODO_USER_ID" \
        $headers \
        -d "$request" \
        -D -)
    
    # Extract session ID from headers if present
    new_session_id=$(echo "$response" | grep -i "Mcp-Session-Id:" | sed 's/.*: //' | tr -d '\r\n')
    if [ -n "$new_session_id" ]; then
        SESSION_ID="$new_session_id"
    fi
    
    # Extract and output just the JSON body
    echo "$response" | sed '1,/^\r$/d'
}

# Main loop - read from stdin, send to HTTP, write to stdout
while IFS= read -r line; do
    if [ -n "$line" ]; then
        send_request "$line"
    fi
done