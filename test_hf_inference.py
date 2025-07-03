#!/usr/bin/env python3
"""
Test HuggingFace hf-inference provider with new API pattern
Created: 2025-07-03 07:45:00 PST
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.ai_providers.huggingface_provider import HuggingFaceProvider
from app.services.dynamic_settings import dynamic_settings

async def test_hf_inference():
    """Test the HuggingFace provider with hf-inference"""
    print("Testing HuggingFace hf-inference provider")
    print("=" * 60)
    
    # Initialize provider
    provider = HuggingFaceProvider()
    
    # Manually set the provider to hf-inference for testing
    print("\n1. Initializing provider...")
    dynamic_settings._loaded = False
    dynamic_settings.HUGGINGFACE_API_TOKEN = "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"  # Your token
    dynamic_settings.HUGGINGFACE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
    dynamic_settings.HUGGINGFACE_PROVIDER = "hf-inference"
    
    initialized = await provider.initialize()
    print(f"   Initialized: {initialized}")
    print(f"   Provider: {provider.provider}")
    print(f"   Model: {provider.model}")
    
    if not initialized:
        print("   Failed to initialize provider!")
        return
    
    # Test availability
    print("\n2. Testing availability...")
    available = await provider.is_available()
    print(f"   Available: {available}")
    
    if not available:
        print("   Provider is not available!")
        return
    
    # Test simple completion
    print("\n3. Testing simple text completion...")
    try:
        response = await provider.complete(
            prompt="What is the capital of France? Answer in one sentence.",
            temperature=0.3,
            max_tokens=50
        )
        print(f"   Response: {response.content}")
        print(f"   Model: {response.model}")
        print(f"   Provider: {response.provider}")
    except Exception as e:
        print(f"   Error: {type(e).__name__}: {str(e)}")
    
    # Test with system prompt
    print("\n4. Testing with system prompt...")
    try:
        response = await provider.complete(
            prompt="Create a task for buying groceries",
            system_prompt="You are a helpful task management assistant. When asked to create a task, respond with a brief acknowledgment.",
            temperature=0.3,
            max_tokens=100
        )
        print(f"   Response: {response.content}")
    except Exception as e:
        print(f"   Error: {type(e).__name__}: {str(e)}")
    
    # Test JSON response format
    print("\n5. Testing JSON response format...")
    try:
        response = await provider.complete(
            prompt="Extract task details from: 'I need to buy milk and bread tomorrow at 5pm'",
            system_prompt="Extract task information and respond in JSON format with fields: title, description, due_date",
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        print(f"   Response: {response.content}")
    except Exception as e:
        print(f"   Error: {type(e).__name__}: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_hf_inference())