"""
Business news crawlers — faithful port of the weekly example script.

Sources (unchanged logic):
  1. ProPakistani Business RSS (paginated WordPress feed)
  2. Arab News /economy archive (+ Jina reader fallback on 403)
  3. Khaleej Times Business via searchadvancestories JSON API

Crawl only — Gemini summaries are applied later by ingest for all news,
with these three sources ordered first so they finish before others.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from config.feeds import NEWS_LOOKBACK_DAYS

# ---- Settings (same as example) ----
LOOKBACK_DAYS = int(os.getenv("BUSINESS_NEWS_LOOKBACK_DAYS", str(NEWS_LOOKBACK_DAYS or 7)))
MAX_PROPAKISTANI_PAGES = int(os.getenv("MAX_PROPAKISTANI_PAGES", "50"))
MAX_ARAB_NEWS_PAGES = int(os.getenv("MAX_ARAB_NEWS_PAGES", "100"))
MAX_ARAB_NEWS_CONSECUTIVE_EMPTY_PAGES = int(
    os.getenv("MAX_ARAB_NEWS_CONSECUTIVE_EMPTY_PAGES", "5")
)
REQUEST_TIMEOUT = int(os.getenv("BUSINESS_NEWS_REQUEST_TIMEOUT", "25"))
REQUEST_DELAY = float(os.getenv("BUSINESS_NEWS_REQUEST_DELAY", "0.5"))
# Cap Gemini volume during testing (0 = no limit)
TEST_LIMIT = int(os.getenv("TEST_LIMIT", "0"))

PROPAKISTANI_BUSINESS_RSS = "https://propakistani.pk/category/business/feed/"
ARAB_NEWS_BUSINESS_ARCHIVE = "https://www.arabnews.com/economy"
KHALEEJ_API_URL = "https://www.khaleejtimes.com/contentapi/v1/searchadvancestories"
KHALEEJ_SECTION_NAME = "Business"
KHALEEJ_PAGE_SIZE = 50
KHALEEJ_MAX_PAGES = 40

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.google.com/",
}

# Feed ids that use this module + Gemini priority summaries
BUSINESS_NEWS_SOURCE_IDS = frozenset(
    {
        "propakistani-business",
        "arab-news-economy",
        "khaleej-times-business",
    }
)


def is_business_news_source(feed: Dict[str, Any]) -> bool:
    """True when this feed should use the example-style crawlers."""
    if feed.get("crawler") == "business_news":
        return True
    return (feed.get("id") or "") in BUSINESS_NEWS_SOURCE_IDS


# ============================================================
# GENERAL HELPERS (from example)
# ============================================================

def clean_text(value: Any) -> str:
    if not value:
        return ""
    value = html.unescape(str(value))
    value = re.sub(r"<script[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_entry_date(entry: Any) -> Optional[datetime]:
    for field in ("published", "updated", "created"):
        value = entry.get(field) if hasattr(entry, "get") else getattr(entry, field, None)
        if value:
            try:
                dt = date_parser.parse(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass

    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(field) if hasattr(entry, "get") else getattr(entry, field, None)
        if value:
            try:
                return datetime(*value[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def normalize_url(url: Any) -> str:
    if not url:
        return ""
    url = html.unescape(str(url)).strip()
    url = url.split("?")[0].split("#")[0]
    return url.rstrip("/")


def extract_categories_from_feed_entry(entry: Any) -> List[str]:
    categories: List[str] = []
    tags = entry.get("tags", []) if hasattr(entry, "get") else getattr(entry, "tags", []) or []
    for tag in tags:
        term = clean_text(tag.get("term", "") if isinstance(tag, dict) else getattr(tag, "term", ""))
        if term:
            categories.append(term)
    return categories


def get_entry_text(entry: Any) -> str:
    content_values = []
    content_list = entry.get("content", []) if hasattr(entry, "get") else getattr(entry, "content", []) or []
    for item in content_list:
        value = clean_text(item.get("value", "") if isinstance(item, dict) else "")
        if value:
            content_values.append(value)

    content = max(content_values, key=len) if content_values else ""
    summary = ""
    if hasattr(entry, "get"):
        summary = entry.get("summary", "") or entry.get("description", "")
    description = clean_text(summary)
    return content if len(content) > len(description) else description


def fetch_url_resilient(url: str, timeout: int = REQUEST_TIMEOUT) -> Tuple[Optional[str], bool]:
    """
    Direct request first; on 403 / connection failure, try r.jina.ai reader proxy.
    Returns (content, is_markdown).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            return resp.text, False
        print(f"      Direct fetch got {resp.status_code} for {url}, trying reader-proxy fallback...")
    except Exception as e:
        print(f"      Direct fetch failed ({type(e).__name__}) for {url}, trying reader-proxy fallback...")

    try:
        proxy_resp = requests.get(f"https://r.jina.ai/{url}", timeout=timeout + 15)
        if proxy_resp.status_code == 200 and proxy_resp.text.strip():
            print(f"      Reader-proxy fallback succeeded for {url}")
            return proxy_resp.text, True
        print(f"      Reader-proxy fallback also failed ({proxy_resp.status_code}) for {url}")
    except Exception as e:
        print(f"      Reader-proxy fallback also failed ({type(e).__name__}) for {url}")

    return None, False


def extract_links_from_markdown(md_text: str, base_domain: str) -> Dict[str, str]:
    links: Dict[str, str] = {}
    for match in re.finditer(r"\[([^\]]*)\]\((https?://[^\s\)]+)\)", md_text):
        text, url = match.group(1), match.group(2)
        if base_domain in url.lower():
            clean_title = clean_text(text)
            if clean_title:
                links[normalize_url(url)] = clean_title
    return links


def parse_date_from_jina_markdown(md_text: str) -> Optional[datetime]:
    match = re.search(r"Published Time:\s*(.+)", md_text)
    if not match:
        return None
    try:
        published = date_parser.parse(match.group(1).strip())
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return published.astimezone(timezone.utc)
    except Exception:
        return None


def fetch_article_meta(url: str, body_class_pattern: str) -> Tuple[Optional[str], Optional[datetime], Optional[str]]:
    """Returns (title, published_dt, text) or (None, None, None) on failure."""
    content, is_markdown = fetch_url_resilient(url)
    if not content:
        return None, None, None

    if is_markdown:
        published = parse_date_from_jina_markdown(content)
        if not published:
            return None, None, None
        title_match = re.search(r"^Title:\s*(.+)$", content, re.MULTILINE)
        title = clean_text(title_match.group(1)) if title_match else None
        body_split = content.split("Markdown Content:", 1)
        raw_body = body_split[1] if len(body_split) > 1 else content
        article_text = clean_text(raw_body)[:5000]
        return title, published, article_text

    try:
        soup = BeautifulSoup(content, "html.parser")

        date_value = None
        for name in ("article:published_time", "publish-date", "date", "pubdate"):
            meta = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
            if meta and meta.get("content"):
                date_value = meta["content"]
                break

        if not date_value:
            for script in soup.find_all("script", type="application/ld+json"):
                raw = script.string or script.get_text(strip=True)
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                    objects = data if isinstance(data, list) else [data]
                    for obj in objects:
                        if isinstance(obj, dict):
                            candidate = obj.get("datePublished") or obj.get("dateCreated")
                            if candidate:
                                date_value = candidate
                                break
                    if date_value:
                        break
                except Exception:
                    pass

        if not date_value:
            return None, None, None

        try:
            published = date_parser.parse(date_value)
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            published = published.astimezone(timezone.utc)
        except Exception:
            return None, None, None

        h1 = soup.find("h1")
        title = clean_text(h1.get_text(" ", strip=True)) if h1 else None

        description = ""
        for attrs in ({"name": "description"}, {"property": "og:description"}):
            meta = soup.find("meta", attrs=attrs)
            if meta and meta.get("content"):
                description = clean_text(meta["content"])
                if description:
                    break

        article_body = ""
        container = soup.find("div", class_=re.compile(body_class_pattern, re.I))
        if container:
            article_body = clean_text(container.get_text(" ", strip=True))

        article_text = article_body if len(article_body) > len(description) else description
        return title, published, article_text
    except Exception:
        return None, None, None


# ============================================================
# PROPAKISTANI
# ============================================================

def crawl_propakistani_business_rss(cutoff: datetime, now: datetime) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    print("\nFetching ProPakistani Business RSS...")

    for page in range(1, MAX_PROPAKISTANI_PAGES + 1):
        url = PROPAKISTANI_BUSINESS_RSS if page == 1 else PROPAKISTANI_BUSINESS_RSS + f"?paged={page}"
        print(f"  ProPakistani RSS page {page}: {url}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as e:
            print(f"    Could not fetch page {page}: {e}")
            break

        entries = feed.entries
        print(f"    entries returned: {len(entries)}")
        if not entries:
            break

        page_rows: List[Dict[str, Any]] = []
        old_entries = 0

        for entry in entries:
            published = parse_entry_date(entry)
            if not published:
                continue
            if published > now:
                continue
            if published < cutoff:
                old_entries += 1
                continue

            title = clean_text(entry.get("title", ""))
            link = normalize_url(entry.get("link", ""))
            if not title or not link or link in seen_urls:
                continue
            seen_urls.add(link)

            categories = extract_categories_from_feed_entry(entry) or ["Business"]

            page_rows.append(
                {
                    "source": "ProPakistani",
                    "title": title,
                    "url": link,
                    "published": published.isoformat(),
                    "categories": categories,
                    "article_text": get_entry_text(entry),
                }
            )

        print(f"    articles in {LOOKBACK_DAYS}-day window: {len(page_rows)}")
        rows.extend(page_rows)

        if old_entries == len(entries):
            print(f"    Reached the {LOOKBACK_DAYS}-day cutoff.")
            break

        time.sleep(REQUEST_DELAY)

    print(f"  ProPakistani articles found: {len(rows)}")
    return rows


# ============================================================
# ARAB NEWS
# ============================================================

def arab_news_is_business_url(url: str) -> bool:
    url = normalize_url(url).lower()
    return "/business-economy" in url or "/business/" in url


def parse_arab_news_archive_page(
    content: str,
    is_markdown: bool,
    cutoff: datetime,
    now: datetime,
    seen_urls: Set[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    page_candidates: Dict[str, str] = {}

    if is_markdown:
        for href, title in extract_links_from_markdown(content, "arabnews.com").items():
            if not arab_news_is_business_url(href):
                continue
            if href in seen_urls or len(title) < 8:
                continue
            page_candidates[href] = title
    else:
        soup = BeautifulSoup(content, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = "https://www.arabnews.com" + href
            if not href.startswith("http") or "arabnews.com" not in href.lower():
                continue
            if not arab_news_is_business_url(href):
                continue

            href = normalize_url(href)
            if href in seen_urls:
                continue

            title = clean_text(a.get_text(" ", strip=True))
            if len(title) < 8:
                continue

            page_candidates[href] = title

    for url, link_title in page_candidates.items():
        title, published, article_text = fetch_article_meta(
            url,
            body_class_pattern=r"(field-name-body|article-body|node__content|content-body)",
        )

        if published is None:
            continue
        if published > now or published < cutoff:
            continue
        if not arab_news_is_business_url(url):
            continue

        seen_urls.add(url)
        rows.append(
            {
                "source": "Arab News",
                "title": title or link_title,
                "url": url,
                "published": published.isoformat(),
                "categories": ["Business & Economy"],
                "article_text": article_text,
            }
        )
        time.sleep(REQUEST_DELAY)

    return rows


def fetch_arab_news_business(cutoff: datetime, now: datetime) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()
    consecutive_empty = 0

    print("\nFetching Arab News Business & Economy archive...")

    for page in range(0, MAX_ARAB_NEWS_PAGES):
        url = ARAB_NEWS_BUSINESS_ARCHIVE if page == 0 else ARAB_NEWS_BUSINESS_ARCHIVE + f"?page={page}"
        print(f"  Arab News archive page {page}: {url}")

        content, is_markdown = fetch_url_resilient(url)
        if not content:
            print(f"    Could not fetch page {page} (direct and reader-proxy both failed)")
            break

        before = len(rows)
        page_rows = parse_arab_news_archive_page(content, is_markdown, cutoff, now, seen_urls)
        rows.extend(page_rows)

        added = len(rows) - before
        print(f"    Business articles added from page: {added}")

        if added == 0:
            consecutive_empty += 1
            if consecutive_empty >= MAX_ARAB_NEWS_CONSECUTIVE_EMPTY_PAGES:
                print(f"    {consecutive_empty} consecutive empty pages, stopping.")
                break
        else:
            consecutive_empty = 0

        time.sleep(REQUEST_DELAY)

    print(f"  Arab News Business articles found: {len(rows)}")
    return rows


# ============================================================
# KHALEEJ TIMES
# ============================================================

def khaleej_is_business_url(url_path: str) -> bool:
    url_path = url_path.lower().strip("/")
    return url_path.startswith("business/") or "/business/" in f"/{url_path}/"


def fetch_khaleej_times_business(cutoff: datetime, now: datetime) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen_slugs: Set[str] = set()
    offset = 0

    print("\nFetching Khaleej Times Business via searchadvancestories API...")

    for _ in range(KHALEEJ_MAX_PAGES):
        params = {
            "section-name": KHALEEJ_SECTION_NAME,
            "sort": "latest-published",
            "limit": KHALEEJ_PAGE_SIZE,
            "offset": offset,
        }

        try:
            resp = requests.get(
                KHALEEJ_API_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"    Could not fetch offset={offset}: {e}")
            break

        stories = (payload.get("data") or {}).get("stories") or []
        print(f"    offset={offset}: {len(stories)} stories returned")

        if not stories:
            break

        reached_cutoff = False

        for story in stories:
            slug = story.get("slug", "")
            url_path = story.get("url") or f"business/{slug}"

            if not khaleej_is_business_url(url_path):
                continue

            published_ms = story.get("first_published_at") or story.get("published_at")
            if published_ms is None:
                continue
            published = datetime.fromtimestamp(published_ms / 1000, tz=timezone.utc)

            if published > now:
                continue
            if published < cutoff:
                reached_cutoff = True
                continue
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            full_url = (
                url_path
                if url_path.startswith("http")
                else f"https://www.khaleejtimes.com/{url_path.lstrip('/')}"
            )
            full_url = normalize_url(full_url)

            api_title = clean_text(story.get("headline", ""))
            api_summary = clean_text(story.get("summary", ""))

            _, _, article_text = fetch_article_meta(
                full_url,
                body_class_pattern=r"(story-element|article-body|story-content|content-body)",
            )
            if not article_text:
                article_text = api_summary

            rows.append(
                {
                    "source": "Khaleej Times",
                    "title": api_title
                    or full_url.rstrip("/").split("/")[-1].replace("-", " ").title(),
                    "url": full_url,
                    "published": published.isoformat(),
                    "categories": ["Business"],
                    "article_text": article_text,
                }
            )
            time.sleep(REQUEST_DELAY)

        if reached_cutoff:
            print(f"    Hit {LOOKBACK_DAYS}-day cutoff, stopping pagination.")
            break

        offset += KHALEEJ_PAGE_SIZE
        time.sleep(REQUEST_DELAY)

    print(f"  Khaleej Times articles found: {len(rows)}")
    return rows


# ============================================================
# Map crawler rows → app feed items + Gemini
# ============================================================

def _item_id(link: str) -> str:
    return hashlib.md5((link or "").encode()).hexdigest()[:50]


def _default_country(source_label: str) -> str:
    if source_label == "ProPakistani":
        return "Pakistan"
    if source_label == "Arab News":
        return "Saudi Arabia"
    if source_label == "Khaleej Times":
        return "United Arab Emirates"
    return "Not specified"


def rows_to_feed_items(rows: List[Dict[str, Any]], feed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert example-script row dicts into the shape the rest of the app expects."""
    items: List[Dict[str, Any]] = []
    for row in rows:
        link = row.get("url") or ""
        text = row.get("article_text") or ""
        cats = list(row.get("categories") or [])
        country = _default_country(row.get("source") or "")
        if country != "Not specified" and country not in cats:
            cats = [country] + cats

        items.append(
            {
                "id": _item_id(link),
                "title": row.get("title") or "",
                "link": link,
                "description": (text[:500] + "…") if len(text) > 500 else text,
                "content": text,
                "pubDate": row.get("published") or "",
                "author": "",
                "categories": cats,
                "source": {
                    "id": feed_config.get("id"),
                    "name": feed_config.get("name"),
                    "url": feed_config.get("url"),
                },
                "country": country,
                "location": country,
                "content_kind": "news",
            }
        )
    return items


def _crawl_sync_for_source(feed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run the matching crawler for one feed id (blocking)."""
    lookback = int(feed_config.get("max_age_days") or LOOKBACK_DAYS)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback)
    sid = feed_config.get("id") or ""

    print("=" * 60)
    print(f"BUSINESS NEWS ({sid}) — last {lookback} days UTC")
    print(f"From: {cutoff.isoformat()}  To: {now.isoformat()}")
    print("=" * 60)

    if sid == "propakistani-business":
        rows = crawl_propakistani_business_rss(cutoff, now)
    elif sid == "arab-news-economy":
        rows = fetch_arab_news_business(cutoff, now)
    elif sid == "khaleej-times-business":
        rows = fetch_khaleej_times_business(cutoff, now)
    else:
        print(f"⚠ Unknown business news source id: {sid}")
        return []

    if TEST_LIMIT and rows:
        print(
            f"⚠ TEST_LIMIT={TEST_LIMIT} — only keeping the {TEST_LIMIT} most recent "
            f"of {len(rows)} for a quick check. Set TEST_LIMIT=0 for a full run."
        )
        rows = sorted(rows, key=lambda r: r.get("published") or "", reverse=True)[:TEST_LIMIT]

    return rows_to_feed_items(rows, feed_config)


async def fetch_business_news_source(feed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Async entry used by ingest: runs sync crawler in a thread.
    Gemini is applied by ingest afterward (priority order + all news).
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _crawl_sync_for_source(feed_config))
