#!/usr/bin/env python3
"""
Test script for voice functionality
Tests the speech transcription API endpoint
"""

import asyncio
import httpx
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))


async def test_voice_endpoint():
    """Test the voice message endpoint with a sample audio file"""
    
    # Configuration
    BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5482")
    API_URL = f"{BASE_URL}/api/v1"
    
    # You'll need to get a valid token first
    # For testing, you can hardcode a token or implement login
    TOKEN = "YOUR_AUTH_TOKEN_HERE"  # Replace with actual token
    
    print("Voice API Test")
    print("=" * 50)
    
    # First, let's test if the endpoint exists
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    # Create a simple test audio file (WAV format)
    # This creates a very short silent WAV file for testing
    import wave
    import struct
    
    test_audio_path = "test_audio.wav"
    
    # Create a simple WAV file
    sample_rate = 16000
    duration = 1  # 1 second
    frequency = 440  # A4 note
    
    with wave.open(test_audio_path, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample
        wav_file.setframerate(sample_rate)
        
        # Generate a simple sine wave
        import math
        for i in range(sample_rate * duration):
            value = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)
    
    print(f"Created test audio file: {test_audio_path}")
    
    # Test the endpoint
    try:
        async with httpx.AsyncClient() as client:
            # Read the audio file
            with open(test_audio_path, 'rb') as f:
                files = {
                    'audio_file': ('test.wav', f, 'audio/wav')
                }
                data = {
                    'language': 'en'
                }
                
                print(f"\nTesting endpoint: {API_URL}/chat/voice-message")
                print("Sending audio file for transcription...")
                
                response = await client.post(
                    f"{API_URL}/chat/voice-message",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=30.0
                )
                
                print(f"\nResponse status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print("\nSuccess! Response:")
                    print(f"Transcription: {result.get('transcription', {})}")
                    if result.get('chatResponse'):
                        print(f"Chat Response: {result['chatResponse']}")
                else:
                    print(f"Error response: {response.text}")
                    
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        # Clean up test file
        if os.path.exists(test_audio_path):
            os.remove(test_audio_path)
            print(f"\nCleaned up test file: {test_audio_path}")


async def test_hf_api_directly():
    """Test HuggingFace API directly to verify it's working"""
    print("\n\nDirect HuggingFace API Test")
    print("=" * 50)
    
    # You need to set your HuggingFace token
    HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
    
    if not HF_TOKEN:
        print("Please set HUGGINGFACE_API_TOKEN environment variable")
        return
    
    # Create a simple test audio
    import wave
    import struct
    
    test_audio_path = "test_hf_audio.wav"
    sample_rate = 16000
    duration = 2  # 2 seconds
    
    with wave.open(test_audio_path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        # Generate silence
        for _ in range(sample_rate * duration):
            wav_file.writeframesraw(b'\x00\x00')
    
    try:
        async with httpx.AsyncClient() as client:
            with open(test_audio_path, 'rb') as f:
                audio_data = f.read()
            
            headers = {
                "Authorization": f"Bearer {HF_TOKEN}"
            }
            
            # Test with whisper-small first
            model = "openai/whisper-small"
            url = f"https://api-inference.huggingface.co/models/{model}"
            
            print(f"Testing model: {model}")
            print("Sending request...")
            
            response = await client.post(
                url,
                headers=headers,
                content=audio_data,
                timeout=30.0
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 503:
                print("\nModel is loading. This is normal for first-time use.")
                print("Please wait and try again in 20-30 seconds.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if os.path.exists(test_audio_path):
            os.remove(test_audio_path)


def main():
    """Run all tests"""
    print("Smart-ToDo Voice Feature Test Suite")
    print("===================================\n")
    
    # Test HuggingFace API directly first
    asyncio.run(test_hf_api_directly())
    
    # Then test our endpoint
    # asyncio.run(test_voice_endpoint())
    
    print("\n\nNote: To test the full endpoint, you need to:")
    print("1. Start the backend server")
    print("2. Get an auth token (login via API or UI)")
    print("3. Update the TOKEN variable in this script")
    print("4. Uncomment the test_voice_endpoint() call")


if __name__ == "__main__":
    main()