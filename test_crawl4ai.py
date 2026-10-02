import asyncio
import sys
import os
from crawl4ai import AsyncWebCrawler

# Fix Windows encoding and event loop
if sys.platform == 'win32':
    # Set UTF-8 encoding for Windows console
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    # Use ProactorEventLoop for Windows (supports subprocess)
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def main():
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(
            url="https://paktender.com",
        )
        if result.success:
            print("✓ Success!")
            print(f"HTML length: {len(result.html)}")
            print(f"Markdown length: {len(result.markdown) if result.markdown else 0}")
            # Check if table is in HTML
            if 'table' in result.html.lower():
                print("✓ Table found in HTML!")
        else:
            print(f"✗ Error: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
