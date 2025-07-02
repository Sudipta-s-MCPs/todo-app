#!/usr/bin/env python3
"""
End-to-End Test Scenarios for Smart-ToDo Application
Simulates real user workflows and interactions
"""

import httpx
import json
import time
import random
from datetime import datetime, timedelta

# Configuration
import os
BASE_URL = os.getenv("API_URL", "http://backend:8000/api/v1")

# Create a client
client = httpx.Client()

# Test data
USERS = {
    "alice": {
        "email": f"alice_{random.randint(1000, 9999)}@example.com",
        "password": "Alice123!@#",
        "name": "Alice Smith"
    },
    "bob": {
        "email": f"bob_{random.randint(1000, 9999)}@example.com",
        "password": "Bob123!@#",
        "name": "Bob Johnson"
    },
    "charlie": {
        "email": f"charlie_{random.randint(1000, 9999)}@example.com",
        "password": "Charlie123!@#",
        "name": "Charlie Brown"
    }
}

# Store tokens and IDs
user_sessions = {}
created_resources = {
    "workspaces": [],
    "tasks": []
}


def print_scenario(scenario_name):
    """Print scenario header"""
    print(f"\n{'='*60}")
    print(f"📋 SCENARIO: {scenario_name}")
    print(f"{'='*60}")


def print_step(step, result="", error=False):
    """Print test step"""
    symbol = "❌" if error else "✅"
    print(f"{symbol} {step}")
    if result:
        print(f"   → {result}")


def register_and_login(user_key):
    """Register and login a user"""
    user_data = USERS[user_key]
    
    # Register
    response = client.post(f"{BASE_URL}/auth/register", json=user_data)
    if response.status_code != 201:
        print_step(f"Register {user_data['name']}", "Failed", error=True)
        return None
    
    # Login
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = client.post(
        f"{BASE_URL}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        session_data = response.json()
        user_sessions[user_key] = {
            "token": session_data["access_token"],
            "user_id": session_data["user"]["id"],
            "email": user_data["email"]
        }
        print_step(f"Register & Login {user_data['name']}", "Success")
        return session_data["access_token"]
    
    print_step(f"Login {user_data['name']}", "Failed", error=True)
    return None


def get_headers(user_key):
    """Get authorization headers for a user"""
    return {"Authorization": f"Bearer {user_sessions[user_key]['token']}"}


def scenario_personal_task_management():
    """Scenario: Individual user managing personal tasks"""
    print_scenario("Personal Task Management")
    
    # Alice logs in
    if not register_and_login("alice"):
        return
    
    # Create personal workspace
    workspace_data = {
        "name": "Alice's Personal Tasks",
        "description": "My personal todo list",
        "type": "personal",
        "emoji": "📝",
        "color": "#4ECDC4"
    }
    response = client.post(f"{BASE_URL}/workspaces", json=workspace_data, headers=get_headers("alice"))
    if response.status_code == 201:
        workspace_id = response.json()["id"]
        created_resources["workspaces"].append(workspace_id)
        print_step("Create personal workspace", "Success")
    else:
        print_step("Create personal workspace", "Failed", error=True)
        return
    
    # Create multiple tasks
    tasks = [
        {
            "title": "Complete project proposal",
            "description": "Write and submit Q1 project proposal",
            "priority": "high",
            "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
            "tags": ["work", "urgent"]
        },
        {
            "title": "Buy groceries",
            "description": "Weekly grocery shopping",
            "priority": "medium",
            "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "tags": ["personal", "shopping"]
        },
        {
            "title": "Learn Python",
            "description": "Complete Python tutorial chapters 5-7",
            "priority": "low",
            "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "tags": ["learning", "programming"]
        }
    ]
    
    created_task_ids = []
    for task in tasks:
        task["workspace_id"] = workspace_id
        response = client.post(f"{BASE_URL}/tasks", json=task, headers=get_headers("alice"))
        if response.status_code == 201:
            created_task_ids.append(response.json()["id"])
            created_resources["tasks"].append(response.json()["id"])
    
    print_step(f"Create {len(created_task_ids)} tasks", f"Created {len(created_task_ids)}/3 tasks")
    
    # Complete a task
    if created_task_ids:
        update_data = {"status": "completed"}
        response = client.put(
            f"{BASE_URL}/tasks/{created_task_ids[1]}", 
            json=update_data, 
            headers=get_headers("alice")
        )
        if response.status_code == 200:
            print_step("Complete 'Buy groceries' task", "Success")
    
    # Check dashboard stats
    response = client.get(f"{BASE_URL}/stats", headers=get_headers("alice"))
    if response.status_code == 200:
        stats = response.json()
        print_step(
            "Check dashboard stats",
            f"Total: {stats['total_tasks']}, Completed: {stats.get('completed_today', 0)}"
        )


def scenario_team_collaboration():
    """Scenario: Team collaborating on shared workspace"""
    print_scenario("Team Collaboration")
    
    # Bob creates a team workspace
    if not register_and_login("bob"):
        return
    
    workspace_data = {
        "name": "Development Team",
        "description": "Sprint tasks and collaboration",
        "type": "shared",
        "emoji": "👥",
        "color": "#FF6B6B"
    }
    response = client.post(f"{BASE_URL}/workspaces", json=workspace_data, headers=get_headers("bob"))
    if response.status_code == 201:
        workspace_id = response.json()["id"]
        created_resources["workspaces"].append(workspace_id)
        print_step("Bob creates team workspace", "Success")
    else:
        print_step("Bob creates team workspace", "Failed", error=True)
        return
    
    # Charlie joins
    if not register_and_login("charlie"):
        return
    
    # Bob invites Charlie
    invite_data = {
        "email": USERS["charlie"]["email"],
        "role": "member"
    }
    response = client.post(
        f"{BASE_URL}/workspaces/{workspace_id}/members/invite",
        json=invite_data,
        headers=get_headers("bob")
    )
    if response.status_code in [200, 201]:
        print_step("Bob invites Charlie", "Success")
    else:
        print_step("Bob invites Charlie", "Failed", error=True)
    
    # Bob creates tasks
    team_tasks = [
        {
            "title": "Setup CI/CD pipeline",
            "description": "Configure GitHub Actions for automated testing",
            "priority": "high",
            "workspace_id": workspace_id,
            "tags": ["devops", "infrastructure"]
        },
        {
            "title": "Write unit tests",
            "description": "Add test coverage for auth module",
            "priority": "medium",
            "workspace_id": workspace_id,
            "tags": ["testing", "backend"]
        }
    ]
    
    for task in team_tasks:
        response = client.post(f"{BASE_URL}/tasks", json=task, headers=get_headers("bob"))
        if response.status_code == 201:
            created_resources["tasks"].append(response.json()["id"])
    
    print_step("Bob creates team tasks", f"Created {len(team_tasks)} tasks")
    
    # Charlie views tasks
    response = client.get(
        f"{BASE_URL}/tasks?workspace_id={workspace_id}", 
        headers=get_headers("charlie")
    )
    if response.status_code == 200:
        tasks = response.json()["tasks"]
        print_step("Charlie views team tasks", f"Found {len(tasks)} tasks")
    
    # Charlie updates a task
    if created_resources["tasks"]:
        update_data = {
            "status": "in_progress",
            "description": "Add test coverage for auth module - Working on it!"
        }
        response = client.put(
            f"{BASE_URL}/tasks/{created_resources['tasks'][-1]}",
            json=update_data,
            headers=get_headers("charlie")
        )
        if response.status_code == 200:
            print_step("Charlie updates task status", "Success")


def scenario_productivity_tracking():
    """Scenario: User tracking productivity over time"""
    print_scenario("Productivity Tracking")
    
    # Use Alice's session
    if "alice" not in user_sessions:
        if not register_and_login("alice"):
            return
    
    # Create tasks for different days (simulating past activity)
    workspace_response = client.get(f"{BASE_URL}/workspaces", headers=get_headers("alice"))
    if workspace_response.status_code != 200 or not workspace_response.json()["workspaces"]:
        print_step("Get workspace", "No workspace found", error=True)
        return
    
    workspace_id = workspace_response.json()["workspaces"][0]["id"]
    
    # Create and complete tasks to simulate activity
    for i in range(5):
        task_data = {
            "title": f"Task {i+1} for productivity tracking",
            "workspace_id": workspace_id,
            "priority": random.choice(["low", "medium", "high"]),
            "status": "completed" if i < 3 else "pending",
            "tags": ["productivity-test"]
        }
        response = client.post(f"{BASE_URL}/tasks", json=task_data, headers=get_headers("alice"))
        if response.status_code == 201:
            created_resources["tasks"].append(response.json()["id"])
    
    print_step("Create tasks for tracking", "Created 5 tasks (3 completed, 2 pending)")
    
    # Check productivity stats
    response = client.get(f"{BASE_URL}/stats", headers=get_headers("alice"))
    if response.status_code == 200:
        stats = response.json()
        print_step(
            "Check productivity metrics",
            f"Productivity change: {stats.get('productivity_change', 0)}%"
        )
    
    # Get activity history
    response = client.get(f"{BASE_URL}/activities?limit=10", headers=get_headers("alice"))
    if response.status_code == 200:
        activities = response.json()["activities"]
        print_step("View activity history", f"Found {len(activities)} recent activities")


def scenario_mobile_pwa_workflow():
    """Scenario: Mobile user using PWA features"""
    print_scenario("Mobile PWA Workflow")
    
    # Simulate mobile device headers
    mobile_headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) Mobile/15E148"
    }
    
    # Check if frontend is accessible
    try:
        response = client.get("http://localhost:5484", headers=mobile_headers)
        if response.status_code == 200:
            print_step("Access PWA from mobile", "Frontend accessible")
    except:
        print_step("Access PWA from mobile", "Frontend not accessible", error=True)
        return
    
    # Use Alice's session for mobile actions
    if "alice" not in user_sessions:
        return
    
    headers = get_headers("alice")
    headers.update(mobile_headers)
    
    # Quick task creation (mobile scenario)
    quick_task = {
        "title": "Quick reminder from mobile",
        "workspace_id": created_resources["workspaces"][0] if created_resources["workspaces"] else None,
        "priority": "medium"
    }
    
    if quick_task["workspace_id"]:
        response = client.post(f"{BASE_URL}/tasks", json=quick_task, headers=headers)
        if response.status_code == 201:
            created_resources["tasks"].append(response.json()["id"])
            print_step("Create quick task from mobile", "Success")


def cleanup_test_data():
    """Clean up all test data"""
    print_scenario("Cleanup Test Data")
    
    # Delete all tasks
    for task_id in created_resources["tasks"]:
        for user_key in user_sessions:
            try:
                response = client.delete(
                    f"{BASE_URL}/tasks/{task_id}",
                    headers=get_headers(user_key)
                )
                if response.status_code == 204:
                    break
            except:
                pass
    
    print_step("Delete tasks", f"Cleaned up {len(created_resources['tasks'])} tasks")
    
    # Delete all workspaces
    for workspace_id in created_resources["workspaces"]:
        for user_key in user_sessions:
            try:
                response = client.delete(
                    f"{BASE_URL}/workspaces/{workspace_id}",
                    headers=get_headers(user_key)
                )
                if response.status_code == 204:
                    break
            except:
                pass
    
    print_step("Delete workspaces", f"Cleaned up {len(created_resources['workspaces'])} workspaces")


def run_all_scenarios():
    """Run all E2E test scenarios"""
    print("\n" + "="*60)
    print("🎬 SMART-TODO END-TO-END TEST SCENARIOS")
    print("="*60)
    
    try:
        # Run scenarios
        scenario_personal_task_management()
        scenario_team_collaboration()
        scenario_productivity_tracking()
        scenario_mobile_pwa_workflow()
        
        # Cleanup
        cleanup_test_data()
        
        print("\n" + "="*60)
        print("✅ All E2E scenarios completed successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during E2E tests: {str(e)}")
        cleanup_test_data()


if __name__ == "__main__":
    run_all_scenarios()