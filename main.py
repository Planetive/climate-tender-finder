# CRITICAL: Set event loop policy BEFORE any other imports that might use asyncio
import sys
import os
import asyncio

# Fix Windows event loop and encoding for Crawl4AI/Playwright
if sys.platform == 'win32':
    # Set UTF-8 encoding for Windows console
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Use ProactorEventLoop for Windows (required for subprocess support - Playwright needs this)
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import uvicorn
from services.unified_service import fetch_all_content
from services.cache_service import get_cached_data, set_cached_data, get_cache_key, clear_cache
from config.feeds import config

app = FastAPI(
    title="News Tracker API",
    description="API for climate funding opportunities from RSS feeds and web scraping",
    version="1.0.0"
)

# CORS: set CORS_ORIGINS=https://your-app.vercel.app,http://localhost:8080
_cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "RSS Feed API is running"
    }


@app.get("/api/feeds")
async def get_feeds(
    limit: int = Query(200, ge=1, le=2000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    refresh: bool = Query(False, description="Force refresh cache (ignore cached data)")
):
    """Get all filtered content from RSS feeds and scraped websites
    
    Uses caching to improve performance. Data is cached for 10 minutes by default.
    Set refresh=true to force a fresh fetch.
    """
    try:
        cache_key = get_cache_key(config["feeds"])
        
        # Try to get cached data first (unless refresh is requested)
        all_feeds = None
        if not refresh:
            all_feeds = await get_cached_data(cache_key)
        
        # If no cached data, fetch fresh data
        if all_feeds is None:
            all_feeds = await fetch_all_content(config["feeds"])
            # Cache the results for 10 minutes
            await set_cached_data(cache_key, all_feeds, ttl_minutes=10)
        
        # Apply pagination
        total = len(all_feeds)
        paginated_feeds = all_feeds[offset:offset + limit]
        
        return {
            "success": True,
            "total": total,
            "count": len(paginated_feeds),
            "offset": offset,
            "limit": limit,
            "data": paginated_feeds,
            "cached": all_feeds is not None and not refresh  # Indicate if data came from cache
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Failed to fetch RSS feeds",
                "message": str(error)
            }
        )


@app.get("/api/feeds/source/{source_id}")
async def get_feeds_by_source(source_id: str):
    """Get feeds from a specific source"""
    try:
        source = next((f for f in config["feeds"] if f["id"] == source_id), None)
        
        if not source:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "Source not found"
                }
            )
        
        feeds = await fetch_all_content([source])
        
        return {
            "success": True,
            "source": source["name"],
            "count": len(feeds),
            "data": feeds
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Failed to fetch RSS feeds from source",
                "message": str(error)
            }
        )


@app.get("/api/sources")
async def get_sources():
    """Get list of all configured sources (RSS feeds and scraping URLs)"""
    sources = [
        {
            "id": feed["id"],
            "name": feed["name"],
            "type": feed.get("type", "rss"),
            "url": feed["url"],
            "description": feed.get("description", "")
        }
        for feed in config["feeds"]
    ]
    
    return {
        "success": True,
        "count": len(sources),
        "data": sources
    }


@app.post("/api/cache/clear")
async def clear_cache_endpoint():
    """Clear the cache (force fresh data on next request)"""
    await clear_cache()
    return {
        "success": True,
        "message": "Cache cleared successfully"
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3001"))
    print(f"🚀 Starting News Tracker API server...")
    rss_count = len([f for f in config['feeds'] if f.get('type', 'rss') == 'rss'])
    scrape_count = len([f for f in config['feeds'] if f.get('type') == 'scrape'])
    print(f"📡 Monitoring {rss_count} RSS feed sources and {scrape_count} scraping sources")
    print(f"🌐 CORS origins: {_cors_origins}")
    print(f"⏳ Initializing server on 0.0.0.0:{port}...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        loop="asyncio"
    )
