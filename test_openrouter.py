"""
Simple test script to verify Google Gemini API key and AI filtering are working
Run this with: python test_openrouter.py
"""

import os
import sys
import asyncio
import re

# Add the project root to the path so we can import our services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to read API key from batch file if not set in environment
# This must be done BEFORE importing the service module
if not os.getenv("GEMINI_API_KEY"):
    batch_file = os.path.join(os.path.dirname(__file__), "start_backend.bat")
    if os.path.exists(batch_file):
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Look for the Gemini API key in the batch file
                match = re.search(r'set GEMINI_API_KEY=(AIzaSy[^\s"]+)', content)
                if match:
                    api_key = match.group(1)
                    os.environ["GEMINI_API_KEY"] = api_key
                    print(f"✓ Loaded Gemini API key from start_backend.bat")
        except Exception as e:
            print(f"⚠ Could not read API key from batch file: {e}")

# Now import the service (it will use the environment variable we just set)
from services.ai_content_filter import check_relevance_with_ai, GEMINI_API_KEY

# Test article - clearly related to climate/sustainability
TEST_ARTICLE_RELEVANT = {
    "title": "New Solar Power Initiative Launches in Pakistan to Reduce Carbon Emissions",
    "description": "A major renewable energy project focusing on solar power to help Pakistan transition to clean energy and reduce greenhouse gas emissions.",
    "content": "The government has announced a new solar power initiative that will help reduce carbon emissions and support the country's transition to renewable energy. This project is part of Pakistan's commitment to sustainable development and climate resilience."
}

# Test article - NOT related to climate/sustainability
TEST_ARTICLE_NOT_RELEVANT = {
    "title": "Local Restaurant Opens New Location Downtown",
    "description": "A popular restaurant chain has opened its third location in the downtown area, offering traditional cuisine.",
    "content": "The restaurant will serve breakfast, lunch, and dinner. It features a modern interior design and can seat up to 100 customers. The grand opening celebration will include live music and special discounts."
}


async def test_openrouter():
    """Test Google Gemini API connection and AI filtering"""
    
    print("=" * 60)
    print("Testing Google Gemini API Connection")
    print("=" * 60)
    print()
    
    # Check if API key is set
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-gemini-api-key-here":
        print("❌ ERROR: Google Gemini API key not set!")
        print()
        print("Please set your API key in one of these ways:")
        print("1. Edit start_backend.bat and replace the API key")
        print("2. Set environment variable: set GEMINI_API_KEY=your-key-here")
        print("3. Or set it in PowerShell: $env:GEMINI_API_KEY='your-key-here'")
        print()
        return False
    
    print(f"✓ API Key found: {GEMINI_API_KEY[:20]}...")
    print()
    
    # Test 1: Check relevant article (should pass)
    print("Test 1: Checking relevant article (should pass)...")
    print(f"   Title: {TEST_ARTICLE_RELEVANT['title']}")
    print()
    
    try:
        result = await check_relevance_with_ai(TEST_ARTICLE_RELEVANT)
        
        if result:
            is_relevant = result.get('is_relevant', False)
            confidence = result.get('confidence', 0)
            reason = result.get('reason', 'No reason provided')
            model_used = result.get('model_used', 'Unknown')
            
            print(f"   ✓ API call successful!")
            print(f"   Model used: {model_used}")
            print(f"   Is relevant: {is_relevant}")
            print(f"   Confidence: {confidence}%")
            print(f"   Reason: {reason}")
            print()
            
            if is_relevant:
                print("   ✅ PASS: Relevant article correctly identified as relevant")
            else:
                print("   ⚠️  WARNING: Relevant article was marked as not relevant")
                print("      This might indicate the AI is being too strict")
        else:
            print("   ❌ FAIL: API call returned no result")
            print("   Check your API key and internet connection")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False
    
    print()
    
    # Test 2: Check non-relevant article (should fail)
    print("Test 2: Checking non-relevant article (should be filtered out)...")
    print(f"   Title: {TEST_ARTICLE_NOT_RELEVANT['title']}")
    print()
    
    try:
        result = await check_relevance_with_ai(TEST_ARTICLE_NOT_RELEVANT)
        
        if result:
            is_relevant = result.get('is_relevant', False)
            confidence = result.get('confidence', 0)
            reason = result.get('reason', 'No reason provided')
            model_used = result.get('model_used', 'Unknown')
            
            print(f"   ✓ API call successful!")
            print(f"   Model used: {model_used}")
            print(f"   Is relevant: {is_relevant}")
            print(f"   Confidence: {confidence}%")
            print(f"   Reason: {reason}")
            print()
            
            if not is_relevant:
                print("   ✅ PASS: Non-relevant article correctly filtered out")
            else:
                print("   ⚠️  WARNING: Non-relevant article was marked as relevant")
                print("      This might indicate the AI is being too lenient")
        else:
            print("   ❌ FAIL: API call returned no result")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False
    
    print()
    print("=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print()
    print("If both tests passed, your Google Gemini setup is working correctly.")
    print("You can now run the backend server and AI filtering will be active.")
    
    return True


if __name__ == "__main__":
    # Set up Windows event loop if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Run the test
    try:
        success = asyncio.run(test_openrouter())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
