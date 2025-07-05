#!/usr/bin/env python3
"""
Comprehensive test script for the lightweight AI implementation
Tests all AI-dependent features with HuggingFace API
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")


def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{RED}❌ {text}{RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {text}{RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{BLUE}ℹ️  {text}{RESET}")


class LightweightAITester:
    """Test harness for the lightweight AI implementation"""
    
    def __init__(self):
        self.results = {
            "configuration": {"passed": False, "details": {}},
            "huggingface_provider": {"passed": False, "details": {}},
            "embeddings": {"passed": False, "details": {}},
            "vector_service": {"passed": False, "details": {}},
            "duplicate_detection": {"passed": False, "details": {}},
            "task_parsing": {"passed": False, "details": {}},
            "semantic_search": {"passed": False, "details": {}},
        }
    
    async def test_configuration(self):
        """Test 1: Verify configuration is set up correctly"""
        print_header("Test 1: Configuration Check")
        
        try:
            from app.services.dynamic_settings import dynamic_settings
            
            # Check if settings are loaded
            if not dynamic_settings._loaded:
                print_info("Loading dynamic settings...")
                await dynamic_settings.refresh()
            
            # Check HuggingFace configuration
            hf_token = dynamic_settings.HUGGINGFACE_API_TOKEN
            if not hf_token:
                print_error("HUGGINGFACE_API_TOKEN not configured")
                print_info("Please set this in admin panel or environment variables")
                self.results["configuration"]["details"]["hf_token"] = "Not configured"
                return
            
            print_success(f"HuggingFace API token configured (length: {len(hf_token)})")
            self.results["configuration"]["details"]["hf_token"] = "Configured"
            
            # Check other AI settings
            ai_enabled = dynamic_settings.ENABLE_AI_FEATURES
            vector_search = dynamic_settings.ENABLE_VECTOR_SEARCH
            ai_duplicate = dynamic_settings.ENABLE_AI_DUPLICATE_DETECTION
            
            print_info(f"AI Features Enabled: {ai_enabled}")
            print_info(f"Vector Search Enabled: {vector_search}")
            print_info(f"AI Duplicate Detection: {ai_duplicate}")
            
            self.results["configuration"]["details"]["ai_features"] = ai_enabled
            self.results["configuration"]["details"]["vector_search"] = vector_search
            self.results["configuration"]["details"]["ai_duplicate"] = ai_duplicate
            
            # Check AI provider configuration
            provider_mode = dynamic_settings.AI_PROVIDER_MODE
            provider_priority = dynamic_settings.AI_PROVIDER_PRIORITY
            
            print_info(f"AI Provider Mode: {provider_mode}")
            print_info(f"Provider Priority: {provider_priority}")
            
            self.results["configuration"]["details"]["provider_mode"] = provider_mode
            self.results["configuration"]["details"]["provider_priority"] = provider_priority
            
            self.results["configuration"]["passed"] = bool(hf_token)
            
        except Exception as e:
            print_error(f"Configuration test failed: {str(e)}")
            self.results["configuration"]["details"]["error"] = str(e)
    
    async def test_huggingface_provider(self):
        """Test 2: Test HuggingFace provider initialization and basic functionality"""
        print_header("Test 2: HuggingFace Provider Test")
        
        try:
            from app.services.ai_providers.huggingface_provider import HuggingFaceProvider
            
            # Initialize provider
            provider = HuggingFaceProvider()
            print_info("Initializing HuggingFace provider...")
            
            if not await provider.initialize():
                print_error("Failed to initialize HuggingFace provider")
                print_info("Check your HUGGINGFACE_API_TOKEN configuration")
                return
            
            print_success("HuggingFace provider initialized successfully")
            self.results["huggingface_provider"]["details"]["initialized"] = True
            
            # Test availability
            is_available = await provider.is_available()
            print_info(f"Provider availability: {is_available}")
            self.results["huggingface_provider"]["details"]["available"] = is_available
            
            # Test basic completion
            if is_available:
                print_info("Testing basic text completion...")
                response = await provider.complete(
                    prompt="Say 'Hello, World!' in JSON format with a 'message' field",
                    temperature=0.1,
                    max_tokens=50,
                    response_format={"type": "json_object"}
                )
                
                print_success(f"Got response: {response.content[:100]}...")
                self.results["huggingface_provider"]["details"]["completion_test"] = "Success"
                self.results["huggingface_provider"]["passed"] = True
            
        except Exception as e:
            print_error(f"HuggingFace provider test failed: {str(e)}")
            self.results["huggingface_provider"]["details"]["error"] = str(e)
    
    async def test_embeddings(self):
        """Test 3: Test embedding generation via HuggingFace API"""
        print_header("Test 3: Embedding Generation Test")
        
        try:
            from app.services.ai_providers.huggingface_provider import HuggingFaceProvider
            
            provider = HuggingFaceProvider()
            if not await provider.initialize():
                print_error("Failed to initialize provider for embeddings")
                return
            
            # Test single embedding
            test_text = "Buy groceries from the store"
            print_info(f"Generating embedding for: '{test_text}'")
            
            embedding = await provider.generate_embedding(test_text)
            print_success(f"Generated embedding with {len(embedding)} dimensions")
            print_info(f"First 5 values: {embedding[:5]}")
            
            self.results["embeddings"]["details"]["single_embedding"] = {
                "dimensions": len(embedding),
                "sample_values": embedding[:5]
            }
            
            # Test batch embeddings
            test_texts = [
                "Complete the project report",
                "Schedule meeting with team",
                "Review pull requests"
            ]
            print_info(f"\nGenerating batch embeddings for {len(test_texts)} texts...")
            
            embeddings = await provider.generate_embeddings_batch(test_texts)
            print_success(f"Generated {len(embeddings)} embeddings")
            
            batch_details = []
            for i, emb in enumerate(embeddings):
                print_info(f"  Text {i+1}: {len(emb)} dimensions")
                batch_details.append({"text_index": i+1, "dimensions": len(emb)})
            
            self.results["embeddings"]["details"]["batch_embeddings"] = batch_details
            self.results["embeddings"]["passed"] = True
            
        except Exception as e:
            print_error(f"Embedding test failed: {str(e)}")
            self.results["embeddings"]["details"]["error"] = str(e)
    
    async def test_vector_service(self):
        """Test 4: Test vector service with HuggingFace embeddings"""
        print_header("Test 4: Vector Service Integration Test")
        
        try:
            from app.services.vector_service import VectorService
            
            # Initialize service
            service = VectorService()
            print_info("Vector service initialized")
            
            # Test embedding generation through vector service
            test_text = "This is a test task for vector service"
            print_info(f"Generating embedding via vector service for: '{test_text}'")
            
            embedding = await service.generate_embedding(test_text)
            
            if all(v == 0.0 for v in embedding):
                print_warning("Got zero embedding - HuggingFace provider might not be initialized")
                self.results["vector_service"]["details"]["embedding_status"] = "Zero embedding"
            else:
                print_success(f"Generated embedding with {len(embedding)} dimensions")
                print_info(f"Non-zero values: {sum(1 for v in embedding if v != 0.0)}")
                self.results["vector_service"]["details"]["embedding_status"] = "Success"
                self.results["vector_service"]["passed"] = True
            
            # Test batch generation
            test_texts = ["Task 1", "Task 2", "Task 3"]
            print_info(f"\nTesting batch embedding generation...")
            
            batch_embeddings = await service.generate_embeddings_batch(test_texts)
            print_success(f"Generated {len(batch_embeddings)} batch embeddings")
            
            self.results["vector_service"]["details"]["batch_count"] = len(batch_embeddings)
            
        except Exception as e:
            print_error(f"Vector service test failed: {str(e)}")
            self.results["vector_service"]["details"]["error"] = str(e)
    
    async def test_duplicate_detection(self):
        """Test 5: Test AI-enhanced duplicate detection"""
        print_header("Test 5: Duplicate Detection Test")
        
        try:
            from app.services.ai_service import get_ai_service
            
            ai_service = get_ai_service()
            
            # Test duplicate detection
            new_task = "Buy milk and eggs from grocery store"
            existing_tasks = [
                {"title": "Buy groceries", "description": "Get milk, eggs, and bread"},
                {"title": "Complete project report", "description": "Finish Q4 report"},
                {"title": "Purchase dairy products", "description": "Need milk and eggs"}
            ]
            
            print_info(f"Testing duplicate detection for: '{new_task}'")
            print_info("Against existing tasks:")
            for task in existing_tasks:
                print_info(f"  - {task['title']}")
            
            analysis = await ai_service.analyze_duplicate(
                new_task=new_task,
                existing_tasks=existing_tasks,
                user_id="test_user"
            )
            
            print_success(f"Duplicate detection completed")
            print_info(f"Is duplicate: {analysis.is_duplicate}")
            print_info(f"Confidence: {analysis.confidence}")
            print_info(f"Reasoning: {analysis.reasoning}")
            print_info(f"Suggested action: {analysis.suggested_action}")
            
            self.results["duplicate_detection"]["details"] = {
                "is_duplicate": analysis.is_duplicate,
                "confidence": analysis.confidence,
                "reasoning": analysis.reasoning,
                "action": analysis.suggested_action
            }
            self.results["duplicate_detection"]["passed"] = True
            
        except Exception as e:
            print_error(f"Duplicate detection test failed: {str(e)}")
            self.results["duplicate_detection"]["details"]["error"] = str(e)
    
    async def test_task_parsing(self):
        """Test 6: Test natural language task parsing"""
        print_header("Test 6: Natural Language Task Parsing Test")
        
        try:
            from app.services.ai_service import get_ai_service
            
            ai_service = get_ai_service()
            
            # Mock workspaces and lists
            workspaces = [
                {"id": "ws1", "name": "Personal"},
                {"id": "ws2", "name": "Work"}
            ]
            lists = [
                {"id": "list1", "name": "Shopping", "workspace_id": "ws1"},
                {"id": "list2", "name": "Projects", "workspace_id": "ws2"}
            ]
            
            # Test natural language parsing
            test_input = "Add task to buy groceries in personal shopping list tomorrow high priority"
            print_info(f"Testing task parsing for: '{test_input}'")
            
            analysis = await ai_service.parse_natural_task(
                natural_text=test_input,
                workspaces=workspaces,
                lists=lists,
                user_id="test_user"
            )
            
            print_success("Task parsing completed")
            print_info(f"Suggested title: {analysis.suggested_title}")
            print_info(f"Workspace: {analysis.suggested_workspace_name}")
            print_info(f"List: {analysis.suggested_list_name}")
            print_info(f"Priority: {analysis.suggested_priority}")
            print_info(f"Due date: {analysis.suggested_due_date}")
            
            self.results["task_parsing"]["details"] = {
                "title": analysis.suggested_title,
                "workspace": analysis.suggested_workspace_name,
                "list": analysis.suggested_list_name,
                "priority": analysis.suggested_priority,
                "due_date": analysis.suggested_due_date
            }
            self.results["task_parsing"]["passed"] = True
            
        except Exception as e:
            print_error(f"Task parsing test failed: {str(e)}")
            self.results["task_parsing"]["details"]["error"] = str(e)
    
    async def test_semantic_search(self):
        """Test 7: Test semantic search capability"""
        print_header("Test 7: Semantic Search Test")
        
        try:
            from app.services.vector_service import get_vector_service
            
            vector_service = get_vector_service()
            
            # Test semantic search (will work if Qdrant is running)
            query = "tasks about shopping and groceries"
            print_info(f"Testing semantic search for: '{query}'")
            
            # Generate query embedding
            embedding = await vector_service.generate_embedding(query)
            
            if all(v == 0.0 for v in embedding):
                print_warning("Got zero embedding - semantic search would not work properly")
                self.results["semantic_search"]["details"]["status"] = "Zero embedding"
            else:
                print_success("Query embedding generated successfully")
                print_info(f"Embedding dimensions: {len(embedding)}")
                print_info(f"Non-zero values: {sum(1 for v in embedding if v != 0.0)}")
                
                self.results["semantic_search"]["details"]["status"] = "Embedding generated"
                self.results["semantic_search"]["details"]["dimensions"] = len(embedding)
                self.results["semantic_search"]["passed"] = True
                
                # Note: Actual search would require Qdrant to be running
                print_info("Note: Actual search requires Qdrant vector database to be running")
            
        except Exception as e:
            print_error(f"Semantic search test failed: {str(e)}")
            self.results["semantic_search"]["details"]["error"] = str(e)
    
    def print_summary(self):
        """Print test summary"""
        print_header("Test Summary")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["passed"])
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        
        print("\nDetailed Results:")
        for test_name, result in self.results.items():
            status = f"{GREEN}PASSED{RESET}" if result["passed"] else f"{RED}FAILED{RESET}"
            print(f"\n{test_name}: {status}")
            
            if result["details"]:
                for key, value in result["details"].items():
                    if key != "error":
                        print(f"  - {key}: {value}")
                    elif not result["passed"]:
                        print(f"  - {RED}Error: {value}{RESET}")
        
        # Overall status
        print("\n" + "=" * 60)
        if passed_tests == total_tests:
            print(f"{GREEN}✅ All tests passed! The lightweight AI implementation is working correctly.{RESET}")
        elif passed_tests > 0:
            print(f"{YELLOW}⚠️  Some tests passed ({passed_tests}/{total_tests}). Check failed tests above.{RESET}")
        else:
            print(f"{RED}❌ All tests failed. Please check your configuration.{RESET}")
        
        # Configuration advice
        if not self.results["configuration"]["passed"]:
            print(f"\n{YELLOW}Configuration Required:{RESET}")
            print("1. Set HUGGINGFACE_API_TOKEN in environment or admin panel")
            print("2. Enable AI features in admin settings")
            print("3. Ensure HuggingFace is in the AI provider priority list")
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print_header("Smart-ToDo Lightweight AI Implementation Test Suite")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run tests in order
        await self.test_configuration()
        
        # Only run other tests if configuration is OK
        if self.results["configuration"]["passed"]:
            await self.test_huggingface_provider()
            await self.test_embeddings()
            await self.test_vector_service()
            await self.test_duplicate_detection()
            await self.test_task_parsing()
            await self.test_semantic_search()
        else:
            print_warning("\nSkipping remaining tests due to configuration issues")
        
        # Print summary
        self.print_summary()


async def main():
    """Main test runner"""
    # Set up minimal environment if not already set
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/test"
    if "REDIS_URL" not in os.environ:
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    if "SECRET_KEY" not in os.environ:
        os.environ["SECRET_KEY"] = "test-secret-key"
    
    # Run tests
    tester = LightweightAITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())