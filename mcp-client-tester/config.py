"""
MCP Client Tester Configuration
Created: 2025-07-01 18:40:00 PST
"""

# Configuration for the MCP client tester
# This is the API key from our registered MCP agent
API_KEY = "sk_todo_dXUp4PpVrpoSHUaN28CQMKJXGuNJZs7vCiTcmxAX"
AGENT_IDENTIFIER = "mcp_K0YxB7lyqgjOZLTv"
DEVICE_NAME = "Test MCP Agent"
API_ENDPOINT = "http://localhost:5482/api/v1"

# Headers for authentication
HEADERS = {
    "X-API-Key": API_KEY,
    "X-Device-ID": AGENT_IDENTIFIER,
    "X-Device-Name": DEVICE_NAME,
    "X-Device-Type": "mcp_agent",
    "Content-Type": "application/json"
}