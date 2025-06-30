#!/usr/bin/env python3
"""
Health check script for Smart-ToDo backend
Created: 2025-01-30 14:52:00 PST
"""

import httpx
import sys
import asyncio


async def check_health():
    """Check if the backend is healthy"""
    url = "http://localhost:8000/health"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Backend is healthy: {data}")
                return True
            else:
                print(f"❌ Backend returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to connect to backend: {e}")
        return False


async def main():
    """Run health check"""
    healthy = await check_health()
    sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    asyncio.run(main())