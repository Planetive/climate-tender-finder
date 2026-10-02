#!/usr/bin/env python3
"""
Test script for MOCC scraper
"""
import asyncio
from services.scraper_service import scrape_single_url
from config.feeds import config

async def test_mocc():
    """Test MOCC scraper"""
    print("=" * 80)
    print("TESTING MOCC NEWS SCRAPER")
    print("=" * 80)
    
    # Find MOCC config
    mocc_config = None
    for feed in config['feeds']:
        if feed['id'] == 'mocc-news':
            mocc_config = feed
            break
    
    if not mocc_config:
        print("✗ MOCC config not found!")
        return
    
    print(f"\n📰 Source: {mocc_config['name']}")
    print(f"🔗 URL: {mocc_config['url']}")
    print(f"🔑 Keywords: {mocc_config['keywords']}")
    print("\nStarting scrape...\n")
    
    results = await scrape_single_url(mocc_config)
    
    print("\n" + "=" * 80)
    print(f"RESULTS: Found {len(results)} news items")
    print("=" * 80)
    
    if results:
        for idx, article in enumerate(results, 1):
            print(f"\n📄 News Item {idx}:")
            print(f"   Title: {article.get('title', 'N/A')[:100]}")
            print(f"   Link: {article.get('link', 'N/A')}")
            print(f"   Description: {article.get('description', 'N/A')[:150]}...")
            print(f"   Published: {article.get('pubDate', 'N/A')}")
            print(f"   Source: {article.get('source', {}).get('name', 'N/A')}")
            if article.get('image'):
                print(f"   Image: {article.get('image')}")
    else:
        print("\n⚠ No news items found!")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_mocc())
