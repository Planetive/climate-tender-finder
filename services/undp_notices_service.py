"""
UNDP official procurement notices via country RSS (Pakistan + UAE).

Feeds (updated hourly by UNDP):
  https://procurement-notices.undp.org/rss_feeds/PAK.xml
  https://procurement-notices.undp.org/rss_feeds/UAE.xml

Why: apply-able UNDP RFPs/ICs beyond the Pakistan country-office page we already scrape.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import feedparser
import httpx

FEED_URLS = {
    "Pakistan": "https://procurement-notices.undp.org/rss_feeds/PAK.xml",
    "United Arab Emirates": "https://procurement-notices.undp.org/rss_feeds/UAE.xml",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NEWS-Tracker/1.0)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def _id(link: str) -> str:
    return hashlib.md5((link or "").encode()).hexdigest()[:50]


def _parse_deadline(entry: Any) -> Optional[str]:
    raw = (
        getattr(entry, "undpprocnot_deadline", None)
        or entry.get("undpprocnot_deadline")
        if hasattr(entry, "get")
        else None
    )
    if not raw:
        summary = entry.get("summary", "") if hasattr(entry, "get") else getattr(entry, "summary", "")
        m = re.search(
            r"Application Deadline:\s*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4})",
            summary or "",
            flags=re.I,
        )
        raw = m.group(1) if m else None
    if not raw:
        return None
    try:
        from dateutil import parser as date_parser

        return date_parser.parse(str(raw), fuzzy=True).date().isoformat()
    except Exception:
        return None


def _map_type(title: str) -> str:
    t = (title or "").lower()
    if any(x in t for x in ("rfp", "request for proposal", "ic-", "consultant", "negotiation")):
        return "RFP"
    if "itb" in t or "invitation to bid" in t:
        return "Tender"
    if "rfq" in t:
        return "RFP"
    return "RFP"


def _entry_to_item(entry: Any, country: str, feed_config: Dict[str, Any]) -> Dict[str, Any]:
    title = (entry.get("title") if hasattr(entry, "get") else getattr(entry, "title", "")) or ""
    link = (entry.get("link") if hasattr(entry, "get") else getattr(entry, "link", "")) or ""
    summary = (
        entry.get("summary") if hasattr(entry, "get") else getattr(entry, "summary", "")
    ) or ""
    deadline = _parse_deadline(entry)
    updated = None
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            updated = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    opp_type = _map_type(title)
    return {
        "id": _id(link or title),
        "title": title.strip(),
        "link": link,
        "description": summary or f"UNDP procurement notice — {country}.",
        "content": summary,
        "pubDate": updated or datetime.now(timezone.utc).isoformat(),
        "deadline": deadline,
        "deadline_display": deadline or "Not specified",
        "author": "UNDP",
        "categories": ["UNDP", country, opp_type],
        "country": country,
        "location": country,
        "opportunity_type": opp_type,
        "content_kind": "opportunity",
        "source": {
            "id": feed_config.get("id", "undp-procurement-pk-uae"),
            "name": feed_config.get("name", "UNDP Procurement (PK + UAE)"),
            "url": feed_config.get("url", "https://procurement-notices.undp.org/"),
        },
    }


async def scrape_undp_pk_uae_notices(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    print("Fetching UNDP procurement RSS (Pakistan + UAE)...")
    items: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(headers=HEADERS, timeout=40.0, follow_redirects=True) as client:
        for country, url in FEED_URLS.items():
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
                entries = feed.entries or []
                print(f"  UNDP {country}: {len(entries)} notices")
                for entry in entries:
                    item = _entry_to_item(entry, country, url_config)
                    if item.get("title") and item.get("link"):
                        items.append(item)
            except Exception as e:
                print(f"  ✗ UNDP {country} feed failed: {e}")

    print(f"[OK] UNDP PK+UAE: {len(items)} notices")
    return items
