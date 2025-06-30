"""MCP Server package for Smart-ToDo"""

from .server import mcp
from .auth import MCPAuthManager

__all__ = ["mcp", "MCPAuthManager"]