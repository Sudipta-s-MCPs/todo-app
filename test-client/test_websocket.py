#!/usr/bin/env python3
"""
WebSocket test client
Created: 2025-01-30 15:03:00 PST
"""

import asyncio
import json
import websockets
import aiohttp
from datetime import datetime
from uuid import uuid4


class WebSocketTestClient:
    def __init__(self, base_url="http://localhost:8000", ws_url="ws://localhost:8000"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.token = None
        self.device_id = f"test-device-{uuid4().hex[:8]}"
        self.workspace_id = None
        self.list_id = None
    
    async def login(self, email="admin@example.com", password="admin123"):
        """Login and get JWT token"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/auth/login",
                data={"username": email, "password": password}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.token = data["access_token"]
                    print(f"✅ Logged in as {email}")
                else:
                    print(f"❌ Login failed: {resp.status}")
    
    async def get_workspace(self):
        """Get first workspace"""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with session.get(
                f"{self.base_url}/api/v1/workspaces",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        self.workspace_id = data[0]["id"]
                        print(f"✅ Using workspace: {data[0]['name']}")
                        
                        # Get first list
                        async with session.get(
                            f"{self.base_url}/api/v1/workspaces/{self.workspace_id}/lists",
                            headers=headers
                        ) as list_resp:
                            if list_resp.status == 200:
                                lists = await list_resp.json()
                                if lists:
                                    self.list_id = lists[0]["id"]
                                    print(f"✅ Using list: {lists[0]['name']}")
    
    async def test_websocket(self):
        """Test WebSocket connection and events"""
        if not self.token:
            print("❌ Not logged in")
            return
        
        # Connect to WebSocket
        ws_url = f"{self.ws_url}/ws?token={self.token}&device_id={self.device_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"✅ Connected to WebSocket")
                
                # Start listening for messages in background
                listen_task = asyncio.create_task(self.listen_messages(websocket))
                
                # Subscribe to workspace
                if self.workspace_id:
                    await websocket.send(json.dumps({
                        "type": "subscribe",
                        "workspace_id": self.workspace_id
                    }))
                    print(f"📤 Subscribed to workspace {self.workspace_id}")
                
                # Send a ping
                await asyncio.sleep(1)
                await websocket.send(json.dumps({"type": "ping"}))
                print("📤 Sent ping")
                
                # Test typing indicator
                await asyncio.sleep(1)
                await websocket.send(json.dumps({
                    "type": "typing",
                    "data": {
                        "workspace_id": self.workspace_id,
                        "is_typing": True
                    }
                }))
                print("📤 Sent typing indicator")
                
                await asyncio.sleep(1)
                await websocket.send(json.dumps({
                    "type": "typing",
                    "data": {
                        "workspace_id": self.workspace_id,
                        "is_typing": False
                    }
                }))
                print("📤 Stopped typing")
                
                # Create a task to trigger notification
                if self.list_id:
                    await self.create_test_task()
                
                # Wait a bit for messages
                await asyncio.sleep(5)
                
                # Cancel listening task
                listen_task.cancel()
                
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
    
    async def listen_messages(self, websocket):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"📥 Received: {data['type']} - {data.get('data', {})}")
        except asyncio.CancelledError:
            pass
    
    async def create_test_task(self):
        """Create a test task to trigger notifications"""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            task_data = {
                "title": f"WebSocket Test Task {datetime.now().strftime('%H:%M:%S')}",
                "description": "This task was created to test WebSocket notifications",
                "priority": "medium",
                "status": "todo"
            }
            
            async with session.post(
                f"{self.base_url}/api/v1/lists/{self.list_id}/tasks",
                headers=headers,
                json=task_data
            ) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    print(f"✅ Created test task: {data['title']}")
                else:
                    print(f"❌ Failed to create task: {resp.status}")


async def main():
    """Run WebSocket tests"""
    print("🚀 Starting WebSocket Test Client")
    print("=" * 50)
    
    client = WebSocketTestClient()
    
    # Login
    await client.login()
    
    # Get workspace
    await client.get_workspace()
    
    # Test WebSocket
    await client.test_websocket()
    
    print("\n✅ WebSocket tests completed!")


if __name__ == "__main__":
    asyncio.run(main())