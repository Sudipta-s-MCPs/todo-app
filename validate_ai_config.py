#!/usr/bin/env python3
"""
Configuration validation script for lightweight AI implementation
Checks all required settings and provides guidance
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def check_mark(condition: bool) -> str:
    return f"{GREEN}✓{RESET}" if condition else f"{RED}✗{RESET}"


async def validate_configuration():
    """Validate AI configuration for lightweight implementation"""
    print_header("Smart-ToDo AI Configuration Validator")
    
    issues = []
    warnings = []
    
    # 1. Check environment variables
    print(f"{BLUE}1. Environment Variables:{RESET}")
    
    env_vars = {
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "REDIS_URL": os.environ.get("REDIS_URL"),
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "HUGGINGFACE_API_TOKEN": os.environ.get("HUGGINGFACE_API_TOKEN"),
    }
    
    for var, value in env_vars.items():
        status = check_mark(bool(value))
        masked_value = "***" + value[-4:] if value and len(value) > 4 else "Not set"
        print(f"  {status} {var}: {masked_value}")
        
        if not value and var in ["DATABASE_URL", "REDIS_URL", "SECRET_KEY"]:
            issues.append(f"Required environment variable {var} is not set")
    
    # 2. Load dynamic settings
    print(f"\n{BLUE}2. Dynamic Settings (from database):{RESET}")
    
    try:
        from app.services.dynamic_settings import dynamic_settings
        
        # Refresh settings
        await dynamic_settings.refresh()
        
        # Check AI-related settings
        settings_to_check = {
            "HUGGINGFACE_API_TOKEN": ("HuggingFace API Token", True),
            "ENABLE_AI_FEATURES": ("AI Features", False),
            "ENABLE_VECTOR_SEARCH": ("Vector Search", False),
            "ENABLE_AI_DUPLICATE_DETECTION": ("AI Duplicate Detection", False),
            "AI_PROVIDER_MODE": ("AI Provider Mode", False),
            "AI_PROVIDER_PRIORITY": ("Provider Priority", False),
            "HUGGINGFACE_MODEL": ("HuggingFace Model", False),
        }
        
        for setting_key, (display_name, is_secret) in settings_to_check.items():
            value = getattr(dynamic_settings, setting_key, None)
            has_value = bool(value)
            status = check_mark(has_value)
            
            if is_secret and value:
                display_value = "***" + str(value)[-4:] if len(str(value)) > 4 else "***"
            else:
                display_value = str(value) if value else "Not configured"
            
            print(f"  {status} {display_name}: {display_value}")
            
            # Check critical settings
            if setting_key == "HUGGINGFACE_API_TOKEN" and not value:
                if not env_vars.get("HUGGINGFACE_API_TOKEN"):
                    issues.append("HUGGINGFACE_API_TOKEN not set in environment or database")
            
            if setting_key == "ENABLE_AI_FEATURES" and not value:
                warnings.append("AI features are disabled - enable in admin panel")
            
            if setting_key == "AI_PROVIDER_PRIORITY" and value and "huggingface" not in str(value).lower():
                warnings.append("HuggingFace not in provider priority list")
        
    except Exception as e:
        issues.append(f"Failed to load dynamic settings: {str(e)}")
        print(f"  {RED}✗ Error loading settings: {str(e)}{RESET}")
    
    # 3. Test HuggingFace provider
    print(f"\n{BLUE}3. HuggingFace Provider Test:{RESET}")
    
    try:
        from app.services.ai_providers.huggingface_provider import HuggingFaceProvider
        
        provider = HuggingFaceProvider()
        initialized = await provider.initialize()
        
        print(f"  {check_mark(initialized)} Provider initialization: {'Success' if initialized else 'Failed'}")
        
        if initialized:
            # Test availability
            available = await provider.is_available()
            print(f"  {check_mark(available)} Provider availability: {'Available' if available else 'Not available'}")
            
            # Test embedding generation
            try:
                test_embedding = await provider.generate_embedding("test")
                embedding_ok = len(test_embedding) > 0
                print(f"  {check_mark(embedding_ok)} Embedding generation: {'Working' if embedding_ok else 'Failed'}")
            except Exception as e:
                print(f"  {RED}✗ Embedding generation: Failed - {str(e)}{RESET}")
                issues.append(f"Embedding generation failed: {str(e)}")
        else:
            issues.append("HuggingFace provider failed to initialize")
            
    except Exception as e:
        issues.append(f"Failed to test HuggingFace provider: {str(e)}")
        print(f"  {RED}✗ Provider test failed: {str(e)}{RESET}")
    
    # 4. Check dependencies
    print(f"\n{BLUE}4. Python Dependencies:{RESET}")
    
    try:
        import huggingface_hub
        print(f"  {GREEN}✓{RESET} huggingface-hub: {huggingface_hub.__version__}")
    except ImportError:
        print(f"  {RED}✗{RESET} huggingface-hub: Not installed")
        issues.append("huggingface-hub package not installed")
    
    try:
        import qdrant_client
        print(f"  {GREEN}✓{RESET} qdrant-client: {qdrant_client.__version__} (optional)")
    except ImportError:
        print(f"  {YELLOW}⚠{RESET} qdrant-client: Not installed (vector search disabled)")
        warnings.append("qdrant-client not installed - vector search will be disabled")
    
    # Check for heavy dependencies that should NOT be present
    heavy_deps = ["sentence_transformers", "torch", "transformers"]
    for dep in heavy_deps:
        try:
            __import__(dep)
            print(f"  {YELLOW}⚠{RESET} {dep}: Installed (not needed for lightweight mode)")
            warnings.append(f"{dep} is installed but not needed - consider removing")
        except ImportError:
            print(f"  {GREEN}✓{RESET} {dep}: Not installed (good - lightweight mode)")
    
    # 5. Summary
    print_header("Validation Summary")
    
    if not issues and not warnings:
        print(f"{GREEN}✅ All checks passed! Your AI configuration is ready.{RESET}")
        print("\nThe lightweight AI implementation is properly configured.")
    else:
        if issues:
            print(f"{RED}Critical Issues ({len(issues)}):{RESET}")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        
        if warnings:
            print(f"\n{YELLOW}Warnings ({len(warnings)}):{RESET}")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
        
        print(f"\n{BLUE}Recommended Actions:{RESET}")
        
        if any("HUGGINGFACE_API_TOKEN" in issue for issue in issues):
            print("\n1. Set HuggingFace API Token:")
            print("   - Option A: Set environment variable")
            print("     export HUGGINGFACE_API_TOKEN='your-token-here'")
            print("   - Option B: Configure in admin panel")
            print("     Go to Admin Panel > Settings > AI Configuration")
            print("\n   Get your token from: https://huggingface.co/settings/tokens")
        
        if any("AI features are disabled" in warning for warning in warnings):
            print("\n2. Enable AI Features:")
            print("   - Go to Admin Panel > Settings")
            print("   - Enable 'AI Features'")
            print("   - Enable 'Vector Search' (if using Qdrant)")
            print("   - Enable 'AI Duplicate Detection'")
        
        if any("provider priority" in warning.lower() for warning in warnings):
            print("\n3. Configure AI Provider Priority:")
            print("   - Go to Admin Panel > Settings")
            print("   - Set AI Provider Priority to include 'huggingface'")
            print("   - Example: 'huggingface,groq,gemini'")
    
    return len(issues) == 0


async def main():
    """Run validation"""
    success = await validate_configuration()
    
    print("\n" + "=" * 60)
    print("For more detailed testing, run: python test_lightweight_implementation.py")
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())