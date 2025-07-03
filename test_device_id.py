#!/usr/bin/env python3
"""Test device ID functionality - 2025-01-30 17:15:00 PST"""

import requests
import json
from datetime import datetime

# API base URL
API_URL = "http://localhost:5482/api/v1"

# Test credentials
USERNAME = "sudipta"
PASSWORD = "Whq3hUdZXY5qQ8"

# Device info for testing
DEVICE_ID = "test-device-123456789"
DEVICE_NAME = "Chrome on macOS"
DEVICE_TYPE = "web"

def test_login_with_device_info():
    """Test login with device headers"""
    print(f"\n{datetime.now()} - Testing login with device info...")
    
    # Login with device headers
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    headers = {
        "X-Device-ID": DEVICE_ID,
        "X-Device-Name": DEVICE_NAME,
        "X-Device-Type": DEVICE_TYPE,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(
        f"{API_URL}/auth/login",
        data=login_data,
        headers=headers
    )
    
    if response.status_code == 200:
        print("✓ Login successful")
        data = response.json()
        access_token = data.get("access_token")
        print(f"✓ Received access token: {access_token[:20]}...")
        return access_token
    else:
        print(f"✗ Login failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return None

def check_devices(access_token):
    """Check user devices"""
    print(f"\n{datetime.now()} - Checking user devices...")
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(
        f"{API_URL}/auth/devices",
        headers=headers
    )
    
    if response.status_code == 200:
        devices = response.json()
        print(f"✓ Found {len(devices)} devices:")
        
        # Find our test device
        test_device_found = False
        for device in devices:
            if device.get("device_identifier") == DEVICE_ID:
                test_device_found = True
                print(f"\n✓ Test device found:")
                print(f"  - ID: {device.get('id')}")
                print(f"  - Name: {device.get('device_name')}")
                print(f"  - Type: {device.get('device_type')}")
                print(f"  - Identifier: {device.get('device_identifier')}")
                print(f"  - Last used: {device.get('last_used_at')}")
                
                # Check if name was updated
                if device.get('device_name') == DEVICE_NAME:
                    print(f"  ✓ Device name correctly set to: {DEVICE_NAME}")
                else:
                    print(f"  ✗ Device name is: {device.get('device_name')}, expected: {DEVICE_NAME}")
            else:
                # Show other devices briefly
                print(f"  - {device.get('device_name')} ({device.get('device_identifier')[:16]}...)")
        
        if not test_device_found:
            print(f"\n✗ Test device with ID {DEVICE_ID} not found")
    else:
        print(f"✗ Failed to get devices: {response.status_code}")
        print(f"  Response: {response.text}")

def main():
    """Run the test"""
    print("=" * 60)
    print("Device ID Test")
    print("=" * 60)
    
    # Test 1: Login with device info
    access_token = test_login_with_device_info()
    
    if access_token:
        # Test 2: Check devices
        check_devices(access_token)
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == "__main__":
    main()