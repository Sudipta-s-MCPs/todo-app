"""
Production-level API tests for Smart-ToDo
Created: 2025-01-30 14:40:00 PST

These tests interact with the live API without mocking.
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import httpx
import pytest
from pydantic import BaseModel
from faker import Faker

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")
TEST_API_KEY = os.getenv("TEST_API_KEY", "")

fake = Faker()


class TestUser(BaseModel):
    """Test user data"""
    email: str
    password: str
    name: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user_id: Optional[str] = None
    api_key: Optional[str] = None


class TestContext:
    """Shared test context"""
    
    def __init__(self):
        self.users: List[TestUser] = []
        self.workspaces: List[Dict[str, Any]] = []
        self.lists: List[Dict[str, Any]] = []
        self.tasks: List[Dict[str, Any]] = []
        self.client: Optional[httpx.AsyncClient] = None
    
    async def setup(self):
        """Setup test context"""
        self.client = httpx.AsyncClient(
            base_url=API_BASE_URL,
            timeout=30.0
        )
    
    async def teardown(self):
        """Cleanup test context"""
        if self.client:
            await self.client.aclose()
    
    async def create_test_user(self) -> TestUser:
        """Create a test user"""
        user = TestUser(
            email=fake.email(),
            password=fake.password(length=12),
            name=fake.name()
        )
        
        # Register user
        response = await self.client.post(
            "/auth/register",
            json={
                "email": user.email,
                "password": user.password,
                "name": user.name
            }
        )
        assert response.status_code == 201
        user_data = response.json()
        user.user_id = user_data["id"]
        
        # Login to get tokens
        response = await self.client.post(
            "/auth/login",
            data={
                "username": user.email,
                "password": user.password
            }
        )
        assert response.status_code == 200
        tokens = response.json()
        user.access_token = tokens["access_token"]
        user.refresh_token = tokens["refresh_token"]
        
        self.users.append(user)
        return user
    
    def get_auth_headers(self, user: TestUser) -> Dict[str, str]:
        """Get authorization headers for a user"""
        if user.api_key:
            return {"X-API-Key": user.api_key}
        elif user.access_token:
            return {"Authorization": f"Bearer {user.access_token}"}
        return {}


# Global test context
ctx = TestContext()


@pytest.fixture(scope="module")
async def test_context():
    """Module-scoped test context"""
    await ctx.setup()
    yield ctx
    await ctx.teardown()


@pytest.mark.asyncio
class TestAuthentication:
    """Test authentication endpoints"""
    
    async def test_user_registration(self, test_context: TestContext):
        """Test user registration"""
        user_data = {
            "email": fake.email(),
            "password": fake.password(length=12),
            "name": fake.name()
        }
        
        response = await test_context.client.post(
            "/auth/register",
            json=user_data
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["email"] == user_data["email"]
        assert result["name"] == user_data["name"]
        assert "id" in result
    
    async def test_user_login(self, test_context: TestContext):
        """Test user login"""
        # Create a user first
        user = await test_context.create_test_user()
        
        # Test login
        response = await test_context.client.post(
            "/auth/login",
            data={
                "username": user.email,
                "password": user.password
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
    
    async def test_api_key_creation(self, test_context: TestContext):
        """Test API key creation"""
        user = await test_context.create_test_user()
        
        response = await test_context.client.post(
            "/auth/api-keys",
            json={
                "name": "Test API Key",
                "permissions": ["tasks:read", "tasks:write"]
            },
            headers=test_context.get_auth_headers(user)
        )
        
        assert response.status_code == 201
        result = response.json()
        assert "key" in result
        assert result["name"] == "Test API Key"
        
        # Save API key for later tests
        user.api_key = result["key"]


@pytest.mark.asyncio
class TestWorkspaces:
    """Test workspace management"""
    
    async def test_create_workspace(self, test_context: TestContext):
        """Test creating a workspace"""
        user = await test_context.create_test_user()
        
        workspace_data = {
            "name": f"Test Workspace {fake.word()}",
            "type": "personal"
        }
        
        response = await test_context.client.post(
            "/workspaces",
            json=workspace_data,
            headers=test_context.get_auth_headers(user)
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == workspace_data["name"]
        assert result["type"] == workspace_data["type"]
        
        test_context.workspaces.append(result)
    
    async def test_list_workspaces(self, test_context: TestContext):
        """Test listing workspaces"""
        user = test_context.users[0] if test_context.users else await test_context.create_test_user()
        
        response = await test_context.client.get(
            "/workspaces",
            headers=test_context.get_auth_headers(user)
        )
        
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) > 0
    
    async def test_workspace_members(self, test_context: TestContext):
        """Test adding members to workspace"""
        # Create two users
        owner = await test_context.create_test_user()
        member = await test_context.create_test_user()
        
        # Create workspace
        workspace_response = await test_context.client.post(
            "/workspaces",
            json={"name": "Shared Workspace", "type": "team"},
            headers=test_context.get_auth_headers(owner)
        )
        workspace = workspace_response.json()
        
        # Add member
        response = await test_context.client.post(
            f"/workspaces/{workspace['id']}/members",
            json={
                "user_email": member.email,
                "role": "member"
            },
            headers=test_context.get_auth_headers(owner)
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["user_email"] == member.email
        assert result["role"] == "member"


@pytest.mark.asyncio
class TestTasks:
    """Test task management"""
    
    async def test_create_task(self, test_context: TestContext):
        """Test creating a task"""
        user = test_context.users[0] if test_context.users else await test_context.create_test_user()
        
        # Get user's lists
        workspaces_response = await test_context.client.get(
            "/workspaces",
            headers=test_context.get_auth_headers(user)
        )
        workspaces = workspaces_response.json()
        
        if workspaces:
            lists_response = await test_context.client.get(
                f"/workspaces/{workspaces[0]['id']}/lists",
                headers=test_context.get_auth_headers(user)
            )
            lists = lists_response.json()
            
            if lists:
                # Create task
                task_data = {
                    "title": f"Test Task {fake.sentence()}",
                    "description": fake.text(),
                    "priority": "medium"
                }
                
                response = await test_context.client.post(
                    f"/lists/{lists[0]['id']}/tasks",
                    json=task_data,
                    headers=test_context.get_auth_headers(user)
                )
                
                assert response.status_code == 201
                result = response.json()
                assert result["title"] == task_data["title"]
                assert result["description"] == task_data["description"]
                
                test_context.tasks.append(result)
    
    async def test_duplicate_detection(self, test_context: TestContext):
        """Test duplicate task detection"""
        user = test_context.users[0] if test_context.users else await test_context.create_test_user()
        
        # Get a list
        workspaces_response = await test_context.client.get(
            "/workspaces",
            headers=test_context.get_auth_headers(user)
        )
        workspaces = workspaces_response.json()
        
        if workspaces:
            lists_response = await test_context.client.get(
                f"/workspaces/{workspaces[0]['id']}/lists",
                headers=test_context.get_auth_headers(user)
            )
            lists = lists_response.json()
            
            if lists:
                # Create first task
                task_data = {
                    "title": "Buy groceries",
                    "description": "Get milk, eggs, and bread"
                }
                
                response1 = await test_context.client.post(
                    f"/lists/{lists[0]['id']}/tasks",
                    json=task_data,
                    headers=test_context.get_auth_headers(user)
                )
                assert response1.status_code == 201
                
                # Try to create duplicate
                response2 = await test_context.client.post(
                    f"/lists/{lists[0]['id']}/tasks",
                    json=task_data,
                    headers=test_context.get_auth_headers(user)
                )
                
                # Should detect duplicate
                assert response2.status_code == 409
                conflict_data = response2.json()
                assert "duplicates" in conflict_data
                assert len(conflict_data["duplicates"]) > 0
    
    async def test_task_search(self, test_context: TestContext):
        """Test task search functionality"""
        user = test_context.users[0] if test_context.users else await test_context.create_test_user()
        
        # Search for tasks
        search_data = {
            "query": "test",
            "limit": 10
        }
        
        response = await test_context.client.post(
            "/tasks/search",
            json=search_data,
            headers=test_context.get_auth_headers(user)
        )
        
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
    
    async def test_task_update(self, test_context: TestContext):
        """Test updating a task"""
        if not test_context.tasks:
            await self.test_create_task(test_context)
        
        if test_context.tasks:
            user = test_context.users[0]
            task = test_context.tasks[0]
            
            update_data = {
                "status": "completed",
                "priority": "high"
            }
            
            response = await test_context.client.put(
                f"/tasks/{task['id']}",
                json=update_data,
                headers=test_context.get_auth_headers(user)
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["priority"] == "high"


@pytest.mark.asyncio
class TestMCPIntegration:
    """Test MCP server integration"""
    
    async def test_mcp_agent_registration(self, test_context: TestContext):
        """Test registering an MCP agent"""
        user = await test_context.create_test_user()
        
        agent_data = {
            "agent_name": "Test MCP Agent",
            "capabilities": ["task_management"],
            "permissions": ["tasks:read", "tasks:write"]
        }
        
        response = await test_context.client.post(
            "/auth/mcp/register",
            json=agent_data,
            headers=test_context.get_auth_headers(user)
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["agent_name"] == agent_data["agent_name"]
        assert "api_key" in result
        assert "agent_identifier" in result


@pytest.mark.asyncio
class TestPerformance:
    """Performance and load tests"""
    
    async def test_concurrent_task_creation(self, test_context: TestContext):
        """Test creating multiple tasks concurrently"""
        user = test_context.users[0] if test_context.users else await test_context.create_test_user()
        
        # Get a list
        workspaces_response = await test_context.client.get(
            "/workspaces",
            headers=test_context.get_auth_headers(user)
        )
        workspaces = workspaces_response.json()
        
        if workspaces:
            lists_response = await test_context.client.get(
                f"/workspaces/{workspaces[0]['id']}/lists",
                headers=test_context.get_auth_headers(user)
            )
            lists = lists_response.json()
            
            if lists:
                # Create 10 tasks concurrently
                tasks = []
                for i in range(10):
                    task_data = {
                        "title": f"Concurrent Task {i} - {fake.sentence()}",
                        "description": fake.text(),
                        "priority": "medium"
                    }
                    
                    task = test_context.client.post(
                        f"/lists/{lists[0]['id']}/tasks",
                        json=task_data,
                        headers=test_context.get_auth_headers(user)
                    )
                    tasks.append(task)
                
                # Wait for all tasks to complete
                responses = await asyncio.gather(*tasks)
                
                # All should succeed
                for response in responses:
                    assert response.status_code == 201


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])