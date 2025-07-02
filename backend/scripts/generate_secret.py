#!/usr/bin/env python3
"""
Generate secure secret key for production use
Created: 2025-01-30 20:00:00 PST
"""

import secrets
import sys


def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure secret key"""
    return secrets.token_urlsafe(length)


def main():
    """Generate and display secret key"""
    print("=" * 60)
    print("SECURE SECRET KEY GENERATOR")
    print("=" * 60)
    print()
    
    # Generate different length keys
    keys = {
        "Standard (32 bytes)": generate_secret_key(32),
        "Strong (64 bytes)": generate_secret_key(64),
        "Extra Strong (128 bytes)": generate_secret_key(128)
    }
    
    for label, key in keys.items():
        print(f"{label}:")
        print(f"  {key}")
        print(f"  Length: {len(key)} characters")
        print()
    
    print("=" * 60)
    print("USAGE:")
    print("Copy one of the above keys and set it as your SECRET_KEY")
    print("environment variable in production.")
    print()
    print("Example in .env file:")
    print(f"SECRET_KEY={keys['Standard (32 bytes)']}")
    print("=" * 60)
    
    # Also generate other secure values
    print("\nOTHER SECURE VALUES:")
    print(f"Admin Password (16 chars): {secrets.token_urlsafe(12)}")
    print(f"Test API Key: {secrets.token_urlsafe(32)}")
    print(f"Database Password: {secrets.token_urlsafe(24)}")


if __name__ == "__main__":
    main()