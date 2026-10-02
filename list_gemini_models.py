"""
Utility script to list available Google Gemini models for your API key.

Run this with:
    python list_gemini_models.py

It will:
- Call the Gemini ListModels endpoint
- Print model IDs and their supported generation methods
- Help you choose a valid model name for AI filtering
"""

import os
import sys
import asyncio
import httpx

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LIST_MODELS_URL = "https://generativelanguage.googleapis.com/v1/models"


async def list_gemini_models() -> bool:
    """Call Gemini ListModels and print the results in a readable way."""
    print("=" * 60)
    print("Listing Google Gemini models for your API key")
    print("=" * 60)
    print()

    if not GEMINI_API_KEY:
        print("❌ ERROR: GEMINI_API_KEY environment variable is not set.")
        print()
        print("Set it in one of these ways:")
        print("  - In PowerShell:   $env:GEMINI_API_KEY='your-key-here'")
        print("  - In cmd:          set GEMINI_API_KEY=your-key-here")
        print("  - Or run via start_backend.bat / start_backend.ps1")
        print()
        return False

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                LIST_MODELS_URL,
                params={"key": GEMINI_API_KEY},
            )

        print(f"HTTP status: {resp.status_code}")
        if resp.status_code != 200:
            print("Raw response (first 500 chars):")
            print(resp.text[:500])
            return False

        data = resp.json()
        models = data.get("models", [])

        if not models:
            print("No models returned. Raw response:")
            print(resp.text[:500])
            return False

        print()
        print(f"Found {len(models)} models. Showing key info:")
        print()

        for m in models:
            name = m.get("name", "unknown")
            display_name = m.get("displayName", "")
            methods = m.get("supportedGenerationMethods", [])

            # Only show models that support generateContent (what we use)
            if "generateContent" not in methods:
                continue

            print(f"- ID: {name}")
            if display_name:
                print(f"  Display: {display_name}")
            print(f"  Methods: {', '.join(methods)}")
            print()

        print("=" * 60)
        print("Tip:")
        print("- Use the value after 'models/' as your model id, e.g.:")
        print("    gemini-1.5-flash")
        print("- Then set it via environment:")
        print("    set AI_FILTER_MODEL=gemini-1.5-flash  (Windows cmd)")
        print("    $env:AI_FILTER_MODEL='gemini-1.5-flash'  (PowerShell)")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"❌ Unexpected error while listing models: {e}")
        return False


if __name__ == "__main__":
    # Windows event loop fix (same pattern as elsewhere)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    ok = asyncio.run(list_gemini_models())
    sys.exit(0 if ok else 1)

