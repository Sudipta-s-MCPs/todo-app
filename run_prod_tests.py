#!/usr/bin/env python3
"""
Production Test Runner for Smart-ToDo
Created: 2025-01-30 15:15:00 PST

Run production tests against the deployed Smart-ToDo application.
This script can be run from any machine that can reach the API.

Usage:
    python run_prod_tests.py --api-url http://192.168.11.100:5482 --api-key your-api-key
"""

import argparse
import sys
import os
import subprocess
import json
from datetime import datetime


def run_tests(api_url, api_key=None, admin_email=None, admin_password=None):
    """Run production tests against the API"""
    
    # Set environment variables for tests
    env = os.environ.copy()
    env['API_BASE_URL'] = api_url
    
    if api_key:
        env['TEST_API_KEY'] = api_key
    
    if admin_email:
        env['ADMIN_EMAIL'] = admin_email
    
    if admin_password:
        env['ADMIN_PASSWORD'] = admin_password
    
    print(f"🚀 Running production tests against: {api_url}")
    print(f"📅 Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Change to test-client directory
    test_dir = os.path.join(os.path.dirname(__file__), 'test-client')
    
    if not os.path.exists(test_dir):
        print("❌ Error: test-client directory not found!")
        print("   Make sure you're running this from the project root.")
        return 1
    
    os.chdir(test_dir)
    
    # Install dependencies if needed
    if not os.path.exists('venv'):
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
        
        # Install requirements
        pip_cmd = 'venv/bin/pip' if os.name != 'nt' else 'venv\\Scripts\\pip.exe'
        print("📦 Installing dependencies...")
        subprocess.run([pip_cmd, 'install', '-r', 'requirements.txt'], check=True)
    
    # Run tests with pytest
    pytest_cmd = 'venv/bin/pytest' if os.name != 'nt' else 'venv\\Scripts\\pytest.exe'
    
    print("\n🧪 Running API tests...")
    result = subprocess.run(
        [pytest_cmd, 'test_api.py', '-v', '--tb=short'],
        env=env
    )
    
    if result.returncode != 0:
        print("\n❌ API tests failed!")
        return result.returncode
    
    print("\n✅ All API tests passed!")
    
    # Run WebSocket tests if requested
    if '--websocket' in sys.argv:
        print("\n🔌 Running WebSocket tests...")
        python_cmd = 'venv/bin/python' if os.name != 'nt' else 'venv\\Scripts\\python.exe'
        result = subprocess.run(
            [python_cmd, 'test_websocket.py'],
            env=env
        )
        
        if result.returncode != 0:
            print("\n❌ WebSocket tests failed!")
            return result.returncode
        
        print("\n✅ WebSocket tests passed!")
    
    print("\n" + "=" * 60)
    print(f"✅ All tests completed successfully!")
    print(f"📅 Finished at: {datetime.now().isoformat()}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Run production tests against Smart-ToDo API'
    )
    parser.add_argument(
        '--api-url',
        default='http://localhost:5482',
        help='API base URL (default: http://localhost:5482)'
    )
    parser.add_argument(
        '--api-key',
        help='API key for authentication'
    )
    parser.add_argument(
        '--admin-email',
        default='admin@example.com',
        help='Admin email for tests'
    )
    parser.add_argument(
        '--admin-password',
        default='admin123',
        help='Admin password for tests'
    )
    parser.add_argument(
        '--websocket',
        action='store_true',
        help='Also run WebSocket tests'
    )
    
    args = parser.parse_args()
    
    # Validate API URL
    if not args.api_url.startswith(('http://', 'https://')):
        print("❌ Error: API URL must start with http:// or https://")
        return 1
    
    # Run tests
    return run_tests(
        args.api_url,
        args.api_key,
        args.admin_email,
        args.admin_password
    )


if __name__ == '__main__':
    sys.exit(main())