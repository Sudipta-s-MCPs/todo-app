#!/usr/bin/env python3
"""
Smart-ToDo MCP Server - Stdio to HTTP Bridge
Self-contained stdio MCP server that connects to Docker HTTP backend
Compatible with Portainer deployment and system Python
Created: 2025-07-04 14:45:00 PST
"""

import sys
import json
import os
import subprocess
import time
import urllib.request
import urllib.parse
import urllib.error
import logging
from typing import Dict, Any, Optional

# Configure logging to stderr (visible in Claude Desktop logs)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class SmartTodoMCPServer:
    """Self-contained stdio MCP server for Smart-ToDo"""
    
    def __init__(self, server_url: str = "http://localhost:5485/mcp/"):
        self.server_url = server_url
        self.initialized = False
        self.session_id = None
        logger.info("Starting Simple MCP Server for Smart-ToDo")
    
    def check_docker_container(self) -> bool:
        """Check if the MCP server container is running"""
        try:
            result = subprocess.run([
                "docker", "ps", "--filter", "name=smart-todo-mcp-server", 
                "--format", "{{.Status}}"
            ], capture_output=True, text=True, timeout=10)
            
            return result.returncode == 0 and "Up" in result.stdout
        except Exception as e:
            logger.error(f"Error checking Docker container: {e}")
            return False

    def start_docker_container(self) -> bool:
        """Start the MCP server container if not running"""
        try:
            # Get project root directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
            
            # Pass authentication credentials from Claude Desktop environment to Docker
            env = os.environ.copy()
            
            # Log which auth credentials we're passing
            if env.get('TODO_API_KEY'):
                logger.info(f"Starting container with API key ending in ...{env['TODO_API_KEY'][-4:]}")
            else:
                logger.warning("No TODO_API_KEY in environment when starting container")
            
            logger.info("Starting Docker container with authentication credentials...")
            result = subprocess.run([
                "docker-compose", "-f", os.path.join(project_root, "docker-compose.yml"),
                "up", "-d", "mcp-server"
            ], capture_output=True, text=True, timeout=60, cwd=project_root, env=env)
            
            if result.returncode != 0:
                logger.error(f"Failed to start Docker container: {result.stderr}")
                return False
            
            # Wait for container to be ready
            for i in range(10):
                time.sleep(2)
                if self.check_docker_container():
                    logger.info("Docker container is running")
                    return True
                    
            logger.error("Docker container failed to start properly")
            return False
            
        except Exception as e:
            logger.error(f"Error starting Docker container: {e}")
            return False

    def forward_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Forward a JSON-RPC request to the HTTP server"""
        try:
            logger.debug(f"Forwarding request: {request.get('method', 'unknown')}")
            
            # Prepare the HTTP request
            data = json.dumps(request).encode('utf-8')
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
                'Content-Length': str(len(data)),
                # Pass authentication credentials from Claude Desktop
                'X-API-Key': os.environ.get('TODO_API_KEY', ''),
                'X-User-ID': os.environ.get('TODO_USER_ID', ''),
                'X-Device-ID': os.environ.get('TODO_DEVICE_ID', ''),
                'X-Device-Name': os.environ.get('TODO_DEVICE_NAME', 'Claude Desktop')
            }
            
            # Add session ID if we have one (for requests after initialization)
            if self.session_id and request.get('method') != 'initialize':
                headers['mcp-session-id'] = self.session_id
            
            req = urllib.request.Request(
                self.server_url,
                data=data,
                headers=headers
            )
            
            # Make the request
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                
                # Extract session ID from headers if available
                try:
                    new_session_id = response.getheader('mcp-session-id')
                    if new_session_id and new_session_id != self.session_id:
                        self.session_id = new_session_id
                        logger.debug(f"Updated session ID: {self.session_id}")
                except (AttributeError, KeyError):
                    pass
                
                # Parse SSE format if needed
                if response_data.startswith('event: '):
                    lines = response_data.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            json_data = line[6:]  # Remove 'data: ' prefix
                            result = json.loads(json_data)
                            logger.debug(f"Got SSE response for method: {request.get('method')}")
                            
                            # Handle initialization response specially
                            if request.get('method') == 'initialize' and 'result' in result:
                                self.initialized = True
                                logger.info("MCP session initialized successfully")
                            
                            return result
                    
                    # If no data line found, return error
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32603,
                            "message": "Invalid SSE response format"
                        }
                    }
                else:
                    # Standard JSON response
                    result = json.loads(response_data)
                    logger.debug(f"Got JSON response for method: {request.get('method')}")
                    
                    # Handle initialization response specially
                    if request.get('method') == 'initialize' and 'result' in result:
                        self.initialized = True
                        logger.info("MCP session initialized successfully")
                    
                    return result
                    
        except urllib.error.HTTPError as e:
            error_text = e.read().decode('utf-8') if e.fp else str(e)
            logger.error(f"HTTP error {e.code}: {error_text}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"HTTP error {e.code}: {error_text}"
                }
            }
        except urllib.error.URLError as e:
            logger.error(f"URL error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Connection error: {str(e)}"
                }
            }
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Request failed: {str(e)}"
                }
            }

    def ensure_server_ready(self) -> bool:
        """Ensure the Docker MCP server is running and accessible"""
        # Check if Docker is available
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.error("Docker is not available")
            return False
        
        # Check if container is running
        if not self.check_docker_container():
            logger.info("MCP server container not running, starting it...")
            if not self.start_docker_container():
                logger.error("Failed to start MCP server container")
                return False
        
        # Test connectivity with a simple request
        try:
            test_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                },
                "id": -1
            }
            
            data = json.dumps(test_request).encode('utf-8')
            req = urllib.request.Request(
                self.server_url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/event-stream'
                }
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.getcode() == 200:
                    logger.info("MCP server is accessible")
                    return True
                    
        except Exception as e:
            logger.error(f"Cannot connect to MCP server: {e}")
            return False
        
        return False

    def run(self) -> int:
        """Main stdio loop"""
        try:
            # Ensure server is ready
            if not self.ensure_server_ready():
                logger.error("MCP server is not ready")
                return 1
            
            logger.info("MCP stdio server ready, waiting for requests...")
            
            # Main stdio loop
            while True:
                try:
                    # Read JSON-RPC request from stdin
                    line = sys.stdin.readline()
                    
                    if not line:  # EOF
                        logger.info("EOF received, shutting down")
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse JSON-RPC request
                    try:
                        request = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON received: {e}")
                        # Send error response
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {
                                "code": -32700,
                                "message": "Parse error"
                            }
                        }
                        print(json.dumps(error_response, separators=(',', ':')), flush=True)
                        continue
                    
                    # Check if we need to initialize first
                    method = request.get('method', '')
                    if method != 'initialize' and not self.initialized:
                        # Send error - server not initialized
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request.get("id"),
                            "error": {
                                "code": -32002,
                                "message": "Server not initialized. Call initialize first."
                            }
                        }
                        response_line = json.dumps(error_response, separators=(',', ':'))
                        print(response_line, flush=True)
                        continue
                    
                    # Forward to HTTP server
                    response = self.forward_request(request)
                    
                    # Send response to stdout
                    response_line = json.dumps(response, separators=(',', ':'))
                    print(response_line, flush=True)
                    
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    # Try to continue
                    continue
                    
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            return 1
        
        logger.info("MCP Server shutting down")
        return 0

def main():
    """Main entry point"""
    try:
        server = SmartTodoMCPServer()
        return server.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())