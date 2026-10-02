"""
Unified service to fetch content from both RSS feeds and web scraping
"""
import os
from typing import List, Dict, Any
from services.rss_service import fetch_and_filter_feeds
from services.scraper_service import scrape_multiple_urls
from services.ai_content_filter import filter_content_with_ai

# Configuration for AI filtering
# Set ENABLE_AI_FILTERING=false to disable AI filtering (uses keyword filtering only)
ENABLE_AI_FILTERING = os.getenv("ENABLE_AI_FILTERING", "false").lower() == "true"
AI_FILTER_MODEL = os.getenv("AI_FILTER_MODEL", None)  # None = use default model
AI_FILTER_BATCH_SIZE = int(os.getenv("AI_FILTER_BATCH_SIZE", "1"))  # 1 at a time for free-tier pacing


async def fetch_all_content(source_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fetch content from both RSS feeds and web scraping sources
    Applies keyword filtering first, then AI filtering if enabled
    
    Args:
        source_configs: List of source configuration dictionaries with 'type' field
        
    Returns:
        Combined list of all content items, sorted by date (newest first)
        Items are filtered to only include content related to climate/sustainability topics
    """
    # Separate RSS feeds and scraping sources
    rss_sources = [s for s in source_configs if s.get('type', 'rss') == 'rss']
    scrape_sources = [s for s in source_configs if s.get('type') == 'scrape']
    
    # Fetch from both sources concurrently
    import asyncio
    
    tasks = []
    if rss_sources:
        tasks.append(fetch_and_filter_feeds(rss_sources))
    if scrape_sources:
        tasks.append(scrape_multiple_urls(scrape_sources))
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks) if tasks else []
    
    # Flatten all items into a single list
    all_items = []
    for items in results:
        all_items.extend(items)
    
    # Apply AI filtering if enabled (sources can opt out via skip_ai_filter)
    if ENABLE_AI_FILTERING and all_items:
        to_filter = []
        skipped = []
        for item in all_items:
            source_id = (item.get("source") or {}).get("id")
            source_cfg = next((s for s in source_configs if s.get("id") == source_id), None)
            if source_cfg and source_cfg.get("skip_ai_filter"):
                skipped.append(item)
            else:
                to_filter.append(item)
        
        print(f"\n🤖 AI Filtering enabled - filtering {len(to_filter)} items for relevance...")
        if skipped:
            print(f"   Skipping AI filter for {len(skipped)} items (skip_ai_filter sources)")
        print(f"   Using model: {AI_FILTER_MODEL or 'default (gemini-2.5-flash)'}")
        print(f"   Batch size: {AI_FILTER_BATCH_SIZE}")
        
        filtered_items = skipped
        if to_filter:
            filtered_items = skipped + await filter_content_with_ai(
                to_filter,
                model=AI_FILTER_MODEL,
                batch_size=AI_FILTER_BATCH_SIZE
            )
        
        print(f"✅ AI filtering complete: {len(filtered_items)}/{len(all_items)} items kept\n")
        all_items = filtered_items
    elif not ENABLE_AI_FILTERING:
        print(f"ℹ️  AI filtering disabled - using keyword filtering only")
        print(f"   To enable AI filtering, set ENABLE_AI_FILTERING=true and GEMINI_API_KEY\n")
    
    # Sort by publication date (newest first)
    all_items.sort(
        key=lambda x: x.get('pubDate', ''),
        reverse=True
    )
    
    return all_items
