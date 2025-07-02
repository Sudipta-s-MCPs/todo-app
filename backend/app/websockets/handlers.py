"""
WebSocket request handlers
Created: 2025-01-30 15:01:00 PST
"""

from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import json
from uuid import UUID
from datetime import datetime

from app.api.dependencies import get_current_user_ws
from app.models.user import User
from .manager import manager
from .events import EventType, WebSocketEvent, TypingIndicator


async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    device_id: str = Query(...)
):
    """
    WebSocket endpoint for real-time updates
    
    Client connects with: ws://localhost:8000/ws?token=<jwt_token>&device_id=<device_id>
    """
    # Authenticate user
    try:
        user = await get_current_user_ws(websocket, token)
        if not user:
            await websocket.close(code=4001, reason="Unauthorized")
            return
    except Exception as e:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Connect
    connection = await manager.connect(websocket, user.id, device_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "ping":
                await manager.handle_ping(connection)
            
            elif message_type == "subscribe":
                # Subscribe to workspace events
                workspace_id = UUID(data.get("workspace_id"))
                await manager.subscribe_to_workspace(connection, workspace_id)
                
                # Send confirmation
                await manager.send_personal_message(
                    connection,
                    WebSocketEvent(
                        type=EventType.CONNECTED,
                        timestamp=datetime.utcnow(),
                        data={"message": f"Subscribed to workspace {workspace_id}"},
                        workspace_id=workspace_id
                    )
                )
            
            elif message_type == "unsubscribe":
                # Unsubscribe from workspace events
                workspace_id = UUID(data.get("workspace_id"))
                await manager.unsubscribe_from_workspace(connection, workspace_id)
            
            elif message_type == "typing":
                # Handle typing indicator
                typing_data = TypingIndicator(**data.get("data", {}))
                typing_data.user_id = user.id
                
                # Broadcast to workspace
                event = WebSocketEvent(
                    type=EventType.USER_TYPING if typing_data.is_typing else EventType.USER_STOPPED_TYPING,
                    timestamp=datetime.utcnow(),
                    data=typing_data.model_dump(mode="json"),
                    workspace_id=typing_data.workspace_id,
                    user_id=user.id
                )
                
                await manager.broadcast_to_workspace(
                    typing_data.workspace_id,
                    event,
                    exclude_user=user.id
                )
            
            elif message_type == "presence":
                # Update user presence
                status = data.get("status", "online")
                if user.id in manager.user_presence:
                    manager.user_presence[user.id].status = status
                    manager.user_presence[user.id].last_seen = datetime.utcnow()
                
                # Broadcast presence update
                await manager.broadcast_user_presence(user.id, status)
            
            else:
                # Unknown message type
                await manager.send_personal_message(
                    connection,
                    WebSocketEvent(
                        type=EventType.ERROR,
                        timestamp=datetime.utcnow(),
                        data={"error": f"Unknown message type: {message_type}"}
                    )
                )
    
    except WebSocketDisconnect:
        await manager.disconnect(connection)
    except Exception as e:
        print(f"WebSocket error for user {user.id}: {e}")
        await manager.disconnect(connection)
        await websocket.close(code=4002, reason="Internal error")