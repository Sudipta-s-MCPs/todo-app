import asyncio
import httpx

async def test_task_detection():
    base_url = 'http://localhost:8000/api/v1'
    
    async with httpx.AsyncClient() as client:
        # Login with a user that has no workspace
        login_resp = await client.post(
            f'{base_url}/auth/login',
            data={'username': 'sudipta.dhara@gmail.com', 'password': 'test123'}
        )
        
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.status_code}")
            print("Creating new user...")
            
            # Register new user
            register_resp = await client.post(
                f'{base_url}/auth/register',
                json={
                    'email': 'test.detection@example.com',
                    'name': 'Test Detection User',
                    'password': 'testpassword123'
                }
            )
            
            if register_resp.status_code not in [201, 400]:  # 400 if user exists
                print(f"Registration failed: {register_resp.status_code}")
                return
                
            # Login again
            login_resp = await client.post(
                f'{base_url}/auth/login',
                data={'username': 'test.detection@example.com', 'password': 'testpassword123'}
            )
            
        if login_resp.status_code != 200:
            print(f"Login still failed: {login_resp.status_code}")
            return
            
        token = login_resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Create a workspace first
        workspace_resp = await client.post(
            f'{base_url}/workspaces/',
            json={
                'name': 'Test Workspace',
                'type': 'personal'
            },
            headers=headers
        )
        
        if workspace_resp.status_code == 201:
            print('Created test workspace')
        else:
            print(f'Workspace creation: {workspace_resp.status_code}')
        
        # Test the problematic message
        test_message = "Schedule meeting with team tomorrow at 3pm"
        print(f"Testing: '{test_message}'")
        
        chat_resp = await client.post(
            f'{base_url}/chat/message',
            json={'content': test_message},
            headers=headers
        )
        
        print(f"Status: {chat_resp.status_code}")
        if chat_resp.status_code == 200:
            result = chat_resp.json()
            print(f"Response: {result['message']['content']}")
            print(f"Used AI: {result.get('usedAI', False)}")
            print(f"Action: {result.get('action')}")
        else:
            print(f"Error: {chat_resp.text}")

asyncio.run(test_task_detection())