#!/usr/bin/env python3
"""
Smart-ToDo MCP Server - Stdio to HTTPS Bridge
Self-contained stdio MCP server that connects to remote HTTPS backend
Updated: 2025-07-05 09:58:00 PST
"""

import sys
import json
import os
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
    
    def __init__(self, server_url: str = "https://todo-mcp.sudiptadhara.in/mcp/"):
        self.server_url = server_url
        self.initialized = False
        self.session_id = None
        logger.info(f"Starting MCP client for remote server at {server_url}")
    

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
        """Ensure the remote MCP server is accessible"""
        logger.info(f"Checking connectivity to remote MCP server at {self.server_url}")
        
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
                    logger.info("Remote MCP server is accessible")
                    return True
                else:
                    logger.error(f"Unexpected response code: {response.getcode()}")
                    return False
                    
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error connecting to MCP server: {e.code} - {e.reason}")
            return False
        except urllib.error.URLError as e:
            logger.error(f"Cannot connect to MCP server at {self.server_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MCP server: {e}")
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