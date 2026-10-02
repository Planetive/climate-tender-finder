import feedparser
import asyncio
import hashlib
import httpx
import ssl
import warnings
from datetime import datetime
from typing import List, Dict, Any
from services.content_filter import filter_relevant_content

# Suppress SSL warnings when verify=False
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


def generate_item_id(link: str, pub_date: str) -> str:
    """Generates a unique ID for a feed item"""
    if link:
        # Use a hash of the URL as ID
        return hashlib.md5(link.encode()).hexdigest()[:50]
    # Fallback to date-based ID
    return hashlib.md5((pub_date or str(datetime.now())).encode()).hexdigest()[:50]


def parse_feed_item(item: feedparser.FeedParserDict, feed_config: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a single RSS feed item into a standardized format"""
    # Handle publication date
    pub_date = None
    if hasattr(item, 'published_parsed') and item.published_parsed:
        pub_date = datetime(*item.published_parsed[:6]).isoformat()
    elif hasattr(item, 'updated_parsed') and item.updated_parsed:
        pub_date = datetime(*item.updated_parsed[:6]).isoformat()
    elif hasattr(item, 'created_parsed') and item.created_parsed:
        # For UNEP custom format - feedparser should parse this automatically
        pub_date = datetime(*item.created_parsed[:6]).isoformat()
    else:
        pub_date = datetime.now().isoformat()
    
    # Extract link - try multiple field names (including UNEP's 'path' field)
    # This should be the URL to the specific article/opportunity, not the feed URL
    link = item.get('link', '')
    if not link:
        # Try 'path' field (UNEP custom format)
        if hasattr(item, 'path'):
            link = item.path
        # Try alternative field names
        elif hasattr(item, 'links') and item.links:
            link = item.links[0].get('href', '')
        elif hasattr(item, 'id'):
            # Sometimes 'id' contains the URL
            link = item.id
    
    # If still no link found, try to use the feed URL as fallback
    # (This is not ideal but better than having no link)
    if not link:
        link = feed_config.get('url', '')
        print(f"  ⚠ Warning: No individual link found for item '{item.get('title', 'Unknown')[:50]}', using feed URL as fallback")
    
    # Extract content - try multiple sources and field names
    content = ""
    description = ""
    
    # Try UNEP custom fields first (field_body and field_synopsis)
    if hasattr(item, 'field_body'):
        body_text = item.field_body
        if body_text:
            # Remove CDATA markers if present
            if isinstance(body_text, str):
                content = body_text
            elif isinstance(body_text, list) and len(body_text) > 0:
                content = body_text[0] if isinstance(body_text[0], str) else str(body_text[0])
    
    if hasattr(item, 'field_synopsis'):
        synopsis_text = item.field_synopsis
        if synopsis_text:
            if isinstance(synopsis_text, str):
                description = synopsis_text
            elif isinstance(synopsis_text, list) and len(synopsis_text) > 0:
                description = synopsis_text[0] if isinstance(synopsis_text[0], str) else str(synopsis_text[0])
            # Use synopsis as content if no body content
            if not content:
                content = description
    
    # Try standard content field (Atom format)
    if not content and hasattr(item, 'content'):
        if isinstance(item.content, list):
            content = ' '.join([c.get('value', '') for c in item.content if isinstance(c, dict)])
        else:
            content = str(item.content)
    
    # Try summary/description fields
    if not description and hasattr(item, 'summary'):
        summary_text = item.summary
        if summary_text:
            description = summary_text
            if not content:
                content = summary_text
    
    if not description and hasattr(item, 'description'):
        desc_text = item.description
        if desc_text:
            description = desc_text
            if not content:
                content = desc_text
    
    # Try title_detail for additional content
    if not content and hasattr(item, 'title_detail') and hasattr(item.title_detail, 'value'):
        title_detail = item.title_detail.value
        if title_detail:
            content = title_detail
    
    # Extract categories/tags
    categories = []
    
    # Try UNEP custom field_related_topics first
    if hasattr(item, 'field_related_topics'):
        topics = item.field_related_topics
        if topics:
            if isinstance(topics, str):
                categories.append(topics)
            elif isinstance(topics, list):
                categories.extend([str(t) for t in topics if t])
    
    # Try standard tags (Atom format)
    if hasattr(item, 'tags') and item.tags:
        # Atom format: tags are a list of dicts with 'term' key
        categories.extend([tag.get('term', '') for tag in item.tags if tag.get('term')])
    elif hasattr(item, 'category'):
        # RSS format: category can be a string or list
        if isinstance(item.category, list):
            categories.extend([cat for cat in item.category if cat])
        elif item.category:
            categories.append(item.category)
    
    # Also check for dc:subject (Dublin Core metadata)
    if hasattr(item, 'dc_subject'):
        if isinstance(item.dc_subject, list):
            categories.extend([subj for subj in item.dc_subject if subj])
        elif item.dc_subject:
            categories.append(item.dc_subject)
    
    # Remove duplicates and empty values
    categories = list(set([cat.strip() for cat in categories if cat and cat.strip()]))
    
    # Extract image - try multiple sources
    image = None
    
    # Try UNEP custom field_article_billboard_image first
    if hasattr(item, 'field_article_billboard_image'):
        billboard_img = item.field_article_billboard_image
        if billboard_img:
            if isinstance(billboard_img, str):
                image = billboard_img
            elif isinstance(billboard_img, list) and len(billboard_img) > 0:
                image = billboard_img[0] if isinstance(billboard_img[0], str) else str(billboard_img[0])
    
    # Try standard media fields
    if not image and hasattr(item, 'media_content'):
        if isinstance(item.media_content, list) and len(item.media_content) > 0:
            image = item.media_content[0].get('url')
    elif not image and hasattr(item, 'enclosures'):
        if isinstance(item.enclosures, list) and len(item.enclosures) > 0:
            if item.enclosures[0].get('type', '').startswith('image'):
                image = item.enclosures[0].get('url')
    
    # Try media_thumbnail
    if not image and hasattr(item, 'media_thumbnail'):
        if isinstance(item.media_thumbnail, list) and len(item.media_thumbnail) > 0:
            image = item.media_thumbnail[0].get('url')
    
    return {
        "id": generate_item_id(link, pub_date),
        "title": item.get('title', 'No title'),
        "link": link,
        "description": description,
        "content": content,
        "pubDate": pub_date,
        "author": item.get('author', feed_config.get('name', 'Unknown')),
        "categories": categories,
        "source": {
            "id": feed_config["id"],
            "name": feed_config["name"],
            "url": feed_config["url"]
        },
        "image": image
    }


async def fetch_single_feed(feed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch and parse a single RSS feed"""
    try:
        print(f"Fetching feed: {feed_config['name']}...")
        
        # Fetch the feed content using httpx with SSL verification disabled
        # (Some feeds have SSL certificate issues)
        # Add headers to avoid 403 Forbidden errors (some servers require User-Agent and Referer)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.afdb.org/',
            'Origin': 'https://www.afdb.org',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        feed = None
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0, headers=headers, follow_redirects=True) as client:
                response = await client.get(feed_config['url'])
                response.raise_for_status()
                feed_content = response.text
                # Parse the RSS feed content
                feed = feedparser.parse(feed_content)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                # If 403, try using feedparser directly (it uses urllib which sometimes works better)
                print(f"⚠ Got 403 with httpx, trying feedparser directly for {feed_config['name']}...")
                feed = feedparser.parse(feed_config['url'])
            else:
                raise
        
        if not feed:
            feed = feedparser.parse(feed_config['url'])
        
        if feed.bozo and feed.bozo_exception:
            print(f"⚠ Warning parsing {feed_config['name']}: {feed.bozo_exception}")
        
        # Debug: Check if feed has entries
        if not feed.entries:
            print(f"⚠ No entries found in {feed_config['name']}")
            return []
        
        # Debug: Log available fields for first item (only for UNEP to avoid spam)
        if feed_config.get('id') == 'unep-news' and len(feed.entries) > 0:
            first_item = feed.entries[0]
            print(f"🔍 Debug - UNEP feed item fields: {list(first_item.keys())}")
            print(f"🔍 Debug - UNEP item 'path': {getattr(first_item, 'path', 'N/A')}")
            print(f"🔍 Debug - UNEP item 'field_body': {hasattr(first_item, 'field_body')}, length: {len(str(getattr(first_item, 'field_body', ''))[:100]) if hasattr(first_item, 'field_body') else 0}")
            print(f"🔍 Debug - UNEP item 'field_synopsis': {hasattr(first_item, 'field_synopsis')}, value: {str(getattr(first_item, 'field_synopsis', 'N/A'))[:100]}")
            print(f"🔍 Debug - UNEP item 'field_article_billboard_image': {getattr(first_item, 'field_article_billboard_image', 'N/A')}")
        
        # Process each item in the feed
        processed_items = [
            parse_feed_item(item, feed_config)
            for item in feed.entries
        ]
        
        # Filter for relevant content
        keywords = feed_config.get('keywords', [])
        relevant_items = [
            item for item in processed_items
            if filter_relevant_content(item, keywords)
        ]
        
        print(f"✓ {feed_config['name']}: Found {len(relevant_items)} relevant items out of {len(processed_items)}")
        
        return relevant_items
    except Exception as error:
        print(f"✗ Error fetching {feed_config['name']}: {str(error)}")
        return []  # Return empty list on error


async def fetch_and_filter_feeds(feed_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fetches and parses RSS feeds from multiple sources
    
    Args:
        feed_configs: List of feed configuration dictionaries
        
    Returns:
        List of parsed and filtered feed items, sorted by date (newest first)
    """
    # Fetch all feeds concurrently
    tasks = [fetch_single_feed(feed_config) for feed_config in feed_configs]
    results = await asyncio.gather(*tasks)
    
    # Flatten all items into a single list
    all_items = []
    for items in results:
        all_items.extend(items)
    
    # Sort by publication date (newest first)
    all_items.sort(
        key=lambda x: x.get('pubDate', ''),
        reverse=True
    )
    
    return all_items
