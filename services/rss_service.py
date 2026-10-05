import feedparser
import asyncio
import hashlib
import httpx
import ssl
import warnings
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from services.content_filter import filter_relevant_content

# Suppress SSL warnings when verify=False
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

_DEFAULT_RSS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


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

    # ADB tender feeds put metadata in one category string, e.g.
    # "Date: 2026-04-10|Project Number: …|Status: Active|Countries: Pakistan|Sectors: Energy"
    adb_meta = parse_adb_category_metadata(categories)
    if adb_meta.get("clean_tags"):
        # Prefer readable tags over the raw pipe-separated blob
        categories = list(dict.fromkeys(adb_meta["clean_tags"] + [
            c for c in categories if "|" not in c
        ]))

    # Prefer ADB category date when feed has no proper pubDate fields
    if adb_meta.get("date") and (
        not hasattr(item, "published_parsed") or not item.published_parsed
    ) and (
        not hasattr(item, "updated_parsed") or not item.updated_parsed
    ):
        pub_date = f"{adb_meta['date']}T00:00:00"
    
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
    
    result = {
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

    # Structured fields for ADB (and any feed using the same category pattern)
    if adb_meta.get("country"):
        result["country"] = adb_meta["country"]
        result["location"] = adb_meta["country"]
    if adb_meta.get("sector"):
        result["development_area"] = adb_meta["sector"]
    if adb_meta.get("status"):
        result["opportunity_type"] = adb_meta["status"]
    if adb_meta.get("project_number"):
        result["reference_number"] = adb_meta["project_number"]
    if adb_meta.get("date"):
        result["posted"] = adb_meta["date"]

    return result


def parse_adb_category_metadata(categories: List[str]) -> Dict[str, Any]:
    """
    Parse ADB FeedBurner category blobs into structured fields.

    Example input category:
    Date: 2026-04-24|Project Number: 53284-002|Status: Active|Countries: Pakistan|Sectors: Energy

    Returns keys: country, sector, status, project_number, date, clean_tags
    Missing parts are omitted (never guessed).
    """
    meta: Dict[str, Any] = {"clean_tags": []}
    blob = next((c for c in categories if "Countries:" in c or "Project Number:" in c), None)
    if not blob:
        return meta

    parts = {}
    for chunk in blob.split("|"):
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", 1)
        parts[key.strip().lower()] = value.strip()

    date = parts.get("date") or ""
    project_number = parts.get("project number") or ""
    status = parts.get("status") or ""
    countries_raw = parts.get("countries") or ""
    sectors = parts.get("sectors") or ""

    if date:
        meta["date"] = date
        meta["clean_tags"].append(f"Date: {date}")
    if project_number:
        meta["project_number"] = project_number
        meta["clean_tags"].append(f"Project: {project_number}")
    if status:
        meta["status"] = status
        meta["clean_tags"].append(status)
    if countries_raw:
        # Keep full label for display/filter (may be "Pakistan" or "Micronesia, Federated States of")
        meta["country"] = countries_raw
        meta["clean_tags"].append(countries_raw)
    if sectors:
        meta["sector"] = sectors
        meta["clean_tags"].append(sectors)

    return meta


def _entry_published_utc(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """Best-effort published time for WordPress / standard RSS entries."""
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        value = getattr(entry, field, None) or entry.get(field)
        if value:
            try:
                return datetime(*value[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for field in ("published", "updated", "created"):
        value = entry.get(field)
        if not value:
            continue
        try:
            # feedparser already normalized most dates; fallback parse via fromisoformat-ish
            parsed = feedparser._parse_date(value) if hasattr(feedparser, "_parse_date") else None
            if parsed:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return None


async def fetch_paginated_wordpress_rss(feed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch WordPress category RSS with ?paged=N (same approach as the working ProPakistani script).
    Stops when a page is empty or every entry on the page is older than max_age_days.
    """
    base_url = feed_config["url"]
    max_pages = int(feed_config.get("max_pages", 20))
    max_age_days = int(feed_config.get("max_age_days", 7))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)

    print(f"Fetching paginated WordPress RSS: {feed_config['name']} (last {max_age_days} days, max {max_pages} pages)")

    all_items: List[Dict[str, Any]] = []
    seen_links: set = set()

    async with httpx.AsyncClient(
        verify=False, timeout=30.0, headers=_DEFAULT_RSS_HEADERS, follow_redirects=True
    ) as client:
        for page in range(1, max_pages + 1):
            # WordPress paging: .../feed/ then .../feed/?paged=2
            if page == 1 or "paged=" in base_url:
                page_url = base_url
            else:
                sep = "&" if "?" in base_url else "?"
                page_url = f"{base_url}{sep}paged={page}"

            print(f"  Page {page}: {page_url}")
            try:
                response = await client.get(page_url)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
            except Exception as e:
                print(f"  ✗ Page {page} failed: {e}")
                break

            entries = feed.entries or []
            print(f"    entries: {len(entries)}")
            if not entries:
                break

            page_kept = 0
            page_old = 0
            for entry in entries:
                published = _entry_published_utc(entry)
                if published and published < cutoff:
                    page_old += 1
                    continue
                if published and published > now + timedelta(days=1):
                    continue

                item = parse_feed_item(entry, feed_config)
                link = (item.get("link") or "").rstrip("/")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                # Structured country for UI filters
                item["country"] = "Pakistan"
                item["location"] = "Pakistan"
                cats = item.get("categories") or []
                if "Pakistan" not in cats:
                    cats = ["Pakistan", "Business"] + cats
                item["categories"] = cats

                all_items.append(item)
                page_kept += 1

            print(f"    kept in window: {page_kept}, older than cutoff: {page_old}")

            # Entire page older than cutoff → stop (feed is newest-first)
            if page_old == len(entries):
                print("  Reached age cutoff — stopping pagination.")
                break

            await asyncio.sleep(0.4)

    print(f"[OK] {feed_config['name']}: {len(all_items)} articles from paginated RSS")
    return all_items


async def fetch_single_feed(feed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch and parse a single RSS feed"""
    try:
        # WordPress category feeds (ProPakistani etc.) — paginate like the standalone crawler
        if feed_config.get("id") == "propakistani-business" or feed_config.get("paginated_wordpress"):
            return await fetch_paginated_wordpress_rss(feed_config)

        print(f"Fetching feed: {feed_config['name']}...")

        headers = {
            **_DEFAULT_RSS_HEADERS,
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.afdb.org/",
            "Origin": "https://www.afdb.org",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        feed = None
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0, headers=headers, follow_redirects=True) as client:
                response = await client.get(feed_config['url'])
                response.raise_for_status()
                feed_content = response.text
                feed = feedparser.parse(feed_content)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                print(f"⚠ Got 403 with httpx, trying feedparser directly for {feed_config['name']}...")
                feed = feedparser.parse(feed_config['url'])
            else:
                raise

        if not feed:
            feed = feedparser.parse(feed_config['url'])

        if feed.bozo and feed.bozo_exception:
            print(f"⚠ Warning parsing {feed_config['name']}: {feed.bozo_exception}")

        if not feed.entries:
            print(f"⚠ No entries found in {feed_config['name']}")
            return []

        if feed_config.get('id') == 'unep-news' and len(feed.entries) > 0:
            first_item = feed.entries[0]
            print(f"🔍 Debug - UNEP feed item fields: {list(first_item.keys())}")

        processed_items = [
            parse_feed_item(item, feed_config)
            for item in feed.entries
        ]

        # skip_ai_filter / skip_keyword_filter = keep all (e.g. ProPakistani business news)
        if feed_config.get("skip_keyword_filter") or feed_config.get("skip_ai_filter"):
            relevant_items = processed_items
        else:
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
