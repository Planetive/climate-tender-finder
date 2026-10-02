# Crawl4ai Setup Instructions

Crawl4ai requires browser dependencies to be installed. Follow these steps:

## 1. Install Crawl4ai

```bash
pip install crawl4ai
```

## 2. Install Browser Dependencies

After installing crawl4ai, run the setup command to install browser binaries (Playwright/Chromium):

```bash
crawl4ai-setup
```

This will download and install the necessary browser binaries automatically.

## 3. Verify Installation

To check if everything is set up correctly:

```bash
crawl4ai-doctor
```

This will verify:
- Python version compatibility
- Playwright installation
- Browser binaries
- Any environment conflicts

## 4. Test Installation

You can test if Crawl4ai is working by running:

```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def test():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://www.example.com")
        print(result.markdown[:300])

asyncio.run(test())
```

## Troubleshooting

If you encounter issues:

1. **Browser not found**: Make sure `crawl4ai-setup` completed successfully
2. **Permission errors**: On Linux/Mac, you may need `sudo` for browser installation
3. **Network issues**: Browser download requires internet connection

## Notes

- The browser binaries are large (~200-300MB) and will be downloaded during setup
- Crawl4ai uses Playwright under the hood for browser automation
- All scraping is done automatically when you call the API - no manual steps needed
