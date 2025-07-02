import asyncio
import httpx

async def test_chat():
    base_url = 'http://localhost:8000/api/v1'
    # First login
    async with httpx.AsyncClient() as client:
        # First create a test user
        register_resp = await client.post(
            f'{base_url}/auth/register',
            json={
                'email': 'test_chat@example.com',
                'name': 'Test Chat User',
                'password': 'testpassword123'
            }
        )
        
        if register_resp.status_code == 201:
            print('Created test user')
        elif register_resp.status_code == 400:
            print('Test user already exists')
        
        # Login
        login_resp = await client.post(
            f'{base_url}/auth/login',
            data={'username': 'test_chat@example.com', 'password': 'testpassword123'}
        )
        
        if login_resp.status_code != 200:
            print(f'Login failed: {login_resp.status_code}')
            print(login_resp.text)
            return
            
        token = login_resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Create a workspace for the test user
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
        
        # Test multiple chat messages
        test_messages = [
            'Show my high priority tasks',
            'Create a task to review Q4 reports',
            'What tasks are due this week?',
            'help'
        ]
        
        for msg in test_messages:
            print(f'\n--- Testing: "{msg}" ---')
            chat_resp = await client.post(
                f'{base_url}/chat/message',
                json={'content': msg},
                headers=headers
            )
            
            print(f'Status: {chat_resp.status_code}')
            if chat_resp.status_code == 200:
                result = chat_resp.json()
                print(f'Response: {result["message"]["content"]}')
                print(f'Used AI: {result.get("usedAI", False)}')
            else:
                print(f'Error: {chat_resp.text}')

asyncio.run(test_chat())