#!/usr/bin/env python3
"""
MCP Client Wrapper for Smart-ToDo
This wrapper connects to the MCP server running in Docker via stdio bridge
Created: 2025-07-03 20:35:00 PST
Updated: 2025-07-04 - Use stdio bridge to Docker HTTP server
"""

import os
import sys
import subprocess
import time

def check_docker_container() -> bool:
    """Check if the MCP server container is running"""
    try:
        result = subprocess.run([
            "docker", "ps", "--filter", "name=smart-todo-mcp-server", 
            "--format", "{{.Status}}"
        ], capture_output=True, text=True, timeout=10)
        
        return result.returncode == 0 and "Up" in result.stdout
    except Exception:
        return False

def start_docker_container() -> bool:
    """Start the MCP server container if not running"""
    try:
        # Get current directory (should be the project root)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Start the MCP server container
        result = subprocess.run([
            "docker-compose", "-f", os.path.join(project_root, "docker-compose.yml"),
            "up", "-d", "mcp-server"
        ], capture_output=True, text=True, timeout=30, cwd=project_root)
        
        if result.returncode != 0:
            print(f"Failed to start Docker container: {result.stderr}", file=sys.stderr)
            return False
        
        # Wait a bit for the container to be ready
        time.sleep(3)
        return check_docker_container()
    except Exception as e:
        print(f"Error starting Docker container: {e}", file=sys.stderr)
        return False

def main():
    """Main entry point"""
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Docker is not available. Please install Docker to use this MCP server.", file=sys.stderr)
        return 1
    
    # Check if container is running
    if not check_docker_container():
        print("MCP server container is not running. Starting it...", file=sys.stderr)
        if not start_docker_container():
            print("Failed to start MCP server container.", file=sys.stderr)
            return 1
    
    print("MCP server container is running.", file=sys.stderr)
    
    # Pass user credentials to the bridge
    env = os.environ.copy()
    
    # Use the stdio bridge to connect to the HTTP server
    bridge_path = os.path.join(os.path.dirname(__file__), "stdio_bridge.py")
    
    try:
        # Execute the bridge - it will handle stdio <-> HTTP conversion
        return subprocess.call([sys.executable, bridge_path], env=env)
    except Exception as e:
        print(f"Error running stdio bridge: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())