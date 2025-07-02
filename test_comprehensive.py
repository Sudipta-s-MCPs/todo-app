import asyncio
import httpx

async def test_comprehensive():
    base_url = 'http://localhost:8000/api/v1'
    
    async with httpx.AsyncClient() as client:
        # Register and login
        register_resp = await client.post(
            f'{base_url}/auth/register',
            json={
                'email': 'comprehensive.test@example.com',
                'name': 'Comprehensive Test User',
                'password': 'testpassword123'
            }
        )
        
        login_resp = await client.post(
            f'{base_url}/auth/login',
            data={'username': 'comprehensive.test@example.com', 'password': 'testpassword123'}
        )
        
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.status_code}")
            return
            
        token = login_resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Create workspace
        workspace_resp = await client.post(
            f'{base_url}/workspaces/',
            json={'name': 'Test Workspace', 'type': 'personal'},
            headers=headers
        )
        
        # Test various natural language inputs
        test_cases = [
            "Schedule meeting with team tomorrow at 3pm",
            "Appointment with doctor next Tuesday",
            "Call John about the project",
            "Meeting with client at 2pm",
            "I need to buy groceries",
            "Don't forget to review the report",
            "Plan the quarterly review",
            "Set up interview with candidate",
            "Arrange conference call with stakeholders",
            "Book flight for next week",
            "Create presentation for Monday",
            "Update the documentation",
            "Send email to team"
        ]
        
        print("Comprehensive Natural Language Test Results:")
        print("=" * 60)
        
        success_count = 0
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i:2d}. Testing: '{test_case}'")
            
            chat_resp = await client.post(
                f'{base_url}/chat/message',
                json={'content': test_case},
                headers=headers
            )
            
            if chat_resp.status_code == 200:
                result = chat_resp.json()
                response = result['message']['content']
                
                if "✅ Created task:" in response:
                    print(f"    ✅ SUCCESS: Task created")
                    success_count += 1
                elif "No workspace found" in response:
                    print(f"    ⚠️  WORKSPACE: {response}")
                elif "You don't have any" in response:
                    print(f"    ℹ️  QUERY: {response}")
                else:
                    print(f"    ❌ FAILED: {response}")
            else:
                print(f"    ❌ ERROR: {chat_resp.status_code}")
        
        print("\n" + "=" * 60)
        print(f"SUCCESS RATE: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")

asyncio.run(test_comprehensive())