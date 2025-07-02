"""
WebSocket connection manager
Created: 2025-01-30 15:01:00 PST
"""

from typing import Dict, List, Set, Optional
from uuid import UUID
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime

from .events import WebSocketEvent, EventType, UserPresence


class Connection:
    """Represents a WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, user_id: UUID, device_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.device_id = device_id
        self.workspace_ids: Set[UUID] = set()
        self.list_ids: Set[UUID] = set()
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        # Active connections by user ID
        self.active_connections: Dict[UUID, List[Connection]] = {}
        # Connections by workspace ID for efficient broadcasting
        self.workspace_connections: Dict[UUID, Set[Connection]] = {}
        # User presence tracking
        self.user_presence: Dict[UUID, UserPresence] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: UUID, device_id: str) -> Connection:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        async with self._lock:
            connection = Connection(websocket, user_id, device_id)
            
            # Add to active connections
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(connection)
            
            # Update user presence
            self.user_presence[user_id] = UserPresence(
                user_id=user_id,
                status="online",
                last_seen=datetime.utcnow()
            )
            
            # Send connection confirmation
            await self.send_personal_message(
                connection,
                WebSocketEvent(
                    type=EventType.CONNECTED,
                    timestamp=datetime.utcnow(),
                    data={"message": "Connected successfully"},
                    user_id=user_id,
                    device_id=device_id
                )
            )
            
            # Notify others about user presence
            await self.broadcast_user_presence(user_id, "online")
            
            return connection
    
    async def disconnect(self, connection: Connection):
        """Remove a WebSocket connection"""
        async with self._lock:
            user_id = connection.user_id
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(connection)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove from workspace connections
            for workspace_id in connection.workspace_ids:
                if workspace_id in self.workspace_connections:
                    self.workspace_connections[workspace_id].discard(connection)
                    if not self.workspace_connections[workspace_id]:
                        del self.workspace_connections[workspace_id]
            
            # Update user presence if no more connections
            if user_id not in self.active_connections:
                if user_id in self.user_presence:
                    self.user_presence[user_id].status = "offline"
                    self.user_presence[user_id].last_seen = datetime.utcnow()
                
                # Notify others about user going offline
                await self.broadcast_user_presence(user_id, "offline")
    
    async def subscribe_to_workspace(self, connection: Connection, workspace_id: UUID):
        """Subscribe a connection to workspace events"""
        async with self._lock:
            connection.workspace_ids.add(workspace_id)
            
            if workspace_id not in self.workspace_connections:
                self.workspace_connections[workspace_id] = set()
            self.workspace_connections[workspace_id].add(connection)
    
    async def unsubscribe_from_workspace(self, connection: Connection, workspace_id: UUID):
        """Unsubscribe a connection from workspace events"""
        async with self._lock:
            connection.workspace_ids.discard(workspace_id)
            
            if workspace_id in self.workspace_connections:
                self.workspace_connections[workspace_id].discard(connection)
                if not self.workspace_connections[workspace_id]:
                    del self.workspace_connections[workspace_id]
    
    async def send_personal_message(self, connection: Connection, event: WebSocketEvent):
        """Send a message to a specific connection"""
        try:
            await connection.websocket.send_json(event.model_dump(mode="json"))
        except Exception as e:
            print(f"Error sending message to {connection.user_id}: {e}")
    
    async def send_to_user(self, user_id: UUID, event: WebSocketEvent):
        """Send a message to all connections of a specific user"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await self.send_personal_message(connection, event)
    
    async def broadcast_to_workspace(
        self,
        workspace_id: UUID,
        event: WebSocketEvent,
        exclude_user: Optional[UUID] = None
    ):
        """Broadcast a message to all connections in a workspace"""
        if workspace_id in self.workspace_connections:
            for connection in self.workspace_connections[workspace_id]:
                if exclude_user and connection.user_id == exclude_user:
                    continue
                await self.send_personal_message(connection, event)
    
    async def broadcast_to_list(
        self,
        workspace_id: UUID,
        list_id: UUID,
        event: WebSocketEvent,
        exclude_user: Optional[UUID] = None
    ):
        """Broadcast a message to all connections interested in a specific list"""
        # For now, broadcast to entire workspace
        # In the future, we could track list-specific subscriptions
        await self.broadcast_to_workspace(workspace_id, event, exclude_user)
    
    async def broadcast_user_presence(self, user_id: UUID, status: str):
        """Broadcast user presence change to relevant connections"""
        event = WebSocketEvent(
            type=EventType.USER_PRESENCE_CHANGED,
            timestamp=datetime.utcnow(),
            data={
                "user_id": str(user_id),
                "status": status,
                "last_seen": datetime.utcnow().isoformat()
            },
            user_id=user_id
        )
        
        # Get all workspaces this user is part of
        # For now, broadcast to all connections (can be optimized later)
        for connections in self.active_connections.values():
            for connection in connections:
                if connection.user_id != user_id:
                    await self.send_personal_message(connection, event)
    
    async def handle_ping(self, connection: Connection):
        """Handle ping message from client"""
        connection.last_ping = datetime.utcnow()
        await self.send_personal_message(
            connection,
            WebSocketEvent(
                type=EventType.CONNECTED,
                timestamp=datetime.utcnow(),
                data={"message": "pong"}
            )
        )
    
    def get_online_users(self, workspace_id: Optional[UUID] = None) -> List[UUID]:
        """Get list of online users, optionally filtered by workspace"""
        if workspace_id and workspace_id in self.workspace_connections:
            return list(set(conn.user_id for conn in self.workspace_connections[workspace_id]))
        return list(self.active_connections.keys())
    
    def get_user_presence(self, user_id: UUID) -> Optional[UserPresence]:
        """Get presence information for a specific user"""
        return self.user_presence.get(user_id)


# Global connection manager instance
manager = ConnectionManager()