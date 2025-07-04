#!/usr/bin/env python3
"""
STDIO to HTTP Bridge for Smart-ToDo MCP Server
This bridges stdio (used by Claude Desktop) to HTTP (used by our Docker MCP server)
Uses only standard library for maximum compatibility
Created: 2025-07-04 14:32:00 PST
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import logging
from typing import Dict, Any

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class StdioHttpBridge:
    """Bridge between stdio and HTTP MCP server using urllib"""
    
    def __init__(self, server_url: str = "http://localhost:5485/mcp/"):
        self.server_url = server_url
        self.session_id = "claude-desktop-session"  # Static session ID for Claude Desktop
    
    def forward_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Forward a JSON-RPC request to the HTTP server"""
        try:
            logger.info(f"Forwarding request: {request.get('method', 'unknown')}")
            
            # Add session ID to the request if not present
            if 'session_id' not in request:
                request['session_id'] = self.session_id
            
            # Prepare the HTTP request
            data = json.dumps(request).encode('utf-8')
            
            req = urllib.request.Request(
                self.server_url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/event-stream',
                    'Content-Length': str(len(data)),
                    'X-Session-ID': self.session_id,
                    'X-MCP-Client': 'claude-desktop'
                }
            )
            
            # Make the request
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                
                # Check if it's SSE format
                if response_data.startswith('event: '):
                    # Parse SSE format: extract the JSON from the data: line
                    lines = response_data.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            json_data = line[6:]  # Remove 'data: ' prefix
                            result = json.loads(json_data)
                            logger.info(f"Got SSE response: {result.get('result', {}).get('status', 'unknown') if 'result' in result else 'error'}")
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
                    logger.info(f"Got JSON response: {result.get('result', {}).get('status', 'unknown') if 'result' in result else 'error'}")
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
    
    def run(self):
        """Main loop: read from stdin, forward to HTTP, write to stdout"""
        logger.info(f"Starting stdio bridge to {self.server_url}")
        
        try:
            # Read from stdin line by line
            while True:
                try:
                    # Read a line from stdin
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
                        continue
                    
                    # Forward to HTTP server
                    response = self.forward_request(request)
                    
                    # Write response to stdout
                    response_line = json.dumps(response, separators=(',', ':'))
                    print(response_line, flush=True)
                    
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            return 1
        
        return 0

def main():
    """Main entry point"""
    # Check if MCP server is accessible
    server_url = "http://localhost:5485/mcp/"
    
    try:
        # Test connection to MCP server with a simple request
        test_request = {
            "jsonrpc": "2.0",
            "method": "initialize", 
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            },
            "id": 0
        }
        data = json.dumps(test_request).encode('utf-8')
        req = urllib.request.Request(
            server_url,
            data=data,
            headers={
                'Content-Type': 'application/json', 
                'Accept': 'application/json, text/event-stream',
                'X-Session-ID': 'claude-desktop-session',
                'X-MCP-Client': 'claude-desktop'
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.getcode() != 200:
                logger.error(f"MCP server not accessible at {server_url}")
                return 1
            logger.info("MCP server is accessible")
    except Exception as e:
        logger.error(f"Cannot connect to MCP server: {e}")
        return 1
    
    # Start the bridge
    bridge = StdioHttpBridge(server_url)
    return bridge.run()

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)