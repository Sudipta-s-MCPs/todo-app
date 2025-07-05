#!/usr/bin/env python3
"""
Test script to verify the lightweight AI implementation
Tests HuggingFace embedding generation via API
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

# Set up minimal environment
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["SECRET_KEY"] = "test-secret-key"


async def test_huggingface_embeddings():
    """Test HuggingFace embedding generation"""
    print("Testing HuggingFace Embedding Generation...")
    
    try:
        from app.services.ai_providers.huggingface_provider import HuggingFaceProvider
        
        # Initialize provider
        provider = HuggingFaceProvider()
        
        # Set up test credentials (you'll need to provide these)
        from app.services.dynamic_settings import dynamic_settings
        # dynamic_settings.HUGGINGFACE_API_TOKEN = "your-hf-token-here"
        
        if not await provider.initialize():
            print("❌ Failed to initialize HuggingFace provider")
            print("   Make sure HUGGINGFACE_API_TOKEN is set in environment or settings")
            return False
        
        print("✅ HuggingFace provider initialized")
        
        # Test single embedding
        test_text = "This is a test task for embedding generation"
        print(f"\nGenerating embedding for: '{test_text}'")
        
        embedding = await provider.generate_embedding(test_text)
        print(f"✅ Generated embedding with {len(embedding)} dimensions")
        print(f"   First 5 values: {embedding[:5]}")
        
        # Test batch embeddings
        test_texts = [
            "Buy groceries from the store",
            "Complete the project report",
            "Schedule meeting with team"
        ]
        print(f"\nGenerating batch embeddings for {len(test_texts)} texts...")
        
        embeddings = await provider.generate_embeddings_batch(test_texts)
        print(f"✅ Generated {len(embeddings)} embeddings")
        for i, emb in enumerate(embeddings):
            print(f"   Text {i+1}: {len(emb)} dimensions")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_vector_service():
    """Test vector service with HuggingFace embeddings"""
    print("\n\nTesting Vector Service with HuggingFace...")
    
    try:
        from app.services.vector_service import VectorService
        
        # Initialize service
        service = VectorService()
        
        # Test embedding generation
        test_text = "This is a test task"
        print(f"\nGenerating embedding via vector service for: '{test_text}'")
        
        embedding = await service.generate_embedding(test_text)
        print(f"✅ Generated embedding with {len(embedding)} dimensions")
        
        # The actual Qdrant operations would fail without a running instance
        # but the embedding generation should work
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Lightweight AI Implementation Test")
    print("=" * 60)
    
    # Test HuggingFace embeddings
    hf_success = await test_huggingface_embeddings()
    
    # Test vector service
    vector_success = await test_vector_service()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  HuggingFace Embeddings: {'✅ PASSED' if hf_success else '❌ FAILED'}")
    print(f"  Vector Service: {'✅ PASSED' if vector_success else '❌ FAILED'}")
    print("=" * 60)
    
    return hf_success and vector_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)