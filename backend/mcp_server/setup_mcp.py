"""
Setup script for MCP server
Created: 2025-01-30 14:38:00 PST

This script helps register the MCP agent and get API credentials.
"""

import asyncio
import sys
from getpass import getpass
from auth import MCPAuthManager


async def main():
    print("Smart-ToDo MCP Server Setup")
    print("=" * 50)
    print()
    
    # Get user credentials
    email = input("Enter your Smart-ToDo email: ")
    password = getpass("Enter your password: ")
    
    print()
    print("Registering MCP agent...")
    
    try:
        auth_manager = MCPAuthManager()
        result = await auth_manager.register_mcp_agent(email, password)
        
        print()
        print("✅ MCP agent registered successfully!")
        print()
        print("Configuration:")
        print("-" * 50)
        print(result["instructions"])
        print("-" * 50)
        print()
        print("Add these environment variables to your .env file or export them")
        print("before running the MCP server.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())