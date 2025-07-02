"""
WebSocket support for real-time updates
Created: 2025-01-30 15:01:00 PST
"""

from .manager import ConnectionManager
from .handlers import websocket_endpoint
from .events import EventType, WebSocketEvent

__all__ = ["ConnectionManager", "websocket_endpoint", "EventType", "WebSocketEvent"]