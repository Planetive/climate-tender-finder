"""
My Tender Notice (Pakistan) — https://mytendernotice.com/

Why: public Pakistan tender aggregator with active notices and Closing Dates.
How: plain HTTP (requests; httpx sometimes gets 403) → parse listing cards →
optional detail page for exact Closing Date.
Scope: homepage "Latest Active" + climate-leaning categories (solar, water, …).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE = "https://mytendernotice.com"
INDEX_URL = f"{BASE}/index.php"

# Categories most relevant to climate / energy / water / infrastructure work
CLIMATE_CATEGORIES = (
    "solar-tender-notice-2026",
    "water-tender-notice-2026",
    "sanitation-tender-notice-2026",
    "generator-tender-notice-2026",
    "fuel-tender-notice-2026",
    "electrical-tender-notice-2026",
    "construction-tender-notice-2026",
    "consultancy-tender-notice-2026",
)

# Soft theme gate for broad categories (electrical / construction / consultancy)
THEME_MARKERS = (
    "solar",
    "renewable",
    "energy",
    "power",
    "climate",
    "environment",
    "water",
    "wastewater",
    "sanitation",
    "sewer",
    "irrigation",
    "desilt",
    "carbon",
    "esg",
    "green",
    "sustainab",
    "generator",
    "fuel",
    "gas",
    "pipeline",
    "grid",
    "transformer",
    "ups",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE + "/",
}

# Cap per category so one broad page (e.g. electrical) cannot flood ingest
MAX_PER_CATEGORY = 25
MAX_DETAIL_FETCHES = 40


def _id(link: str) -> str:
    return hashlib.md5((link or "").encode()).hexdigest()[:50]


def _fetch_html(url: str) -> Optional[str]:
    """Fetch HTML. Prefer requests (site often blocks httpx)."""
    try:
        import requests

        resp = requests.get(url, headers=HEADERS, timeout=40)
        if resp.status_code == 200 and resp.text:
            return resp.text
        print(f"  mytendernotice requests status {resp.status_code} for {url}")
    except Exception as e:
        print(f"  mytendernotice requests failed ({e}), trying httpx…")

    try:
        import httpx

        with httpx.Client(
            headers=HEADERS, timeout=40.0, follow_redirects=True
        ) as client:
            resp = client.get(url)
            if resp.status_code == 200 and resp.text:
                return resp.text
            print(f"  mytendernotice httpx status {resp.status_code} for {url}")
    except Exception as e2:
        print(f"  mytendernotice fetch failed: {e2}")
    return None


def _parse_closing_date(text: str) -> Optional[str]:
    """Extract Closing Date like '16 Dec 2026' → ISO."""
    if not text:
        return None
    m = re.search(
        r"Closing\s*Date\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        text,
        flags=re.I,
    )
    if not m:
        return None
    try:
        from dateutil import parser as date_parser

        return date_parser.parse(m.group(1), fuzzy=True).date().isoformat()
    except Exception:
        return None


def _deadline_from_days_left(days: int) -> str:
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def _has_theme(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in THEME_MARKERS)


def _parse_cards(
    html: str, require_theme: bool = False
) -> List[Dict[str, Any]]:
    """Pull tender cards (title, summary, city, days left, detail link)."""
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []

    for card in soup.select(".card"):
        title_el = card.select_one(".card-title, h5")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        if not title:
            continue

        desc_el = card.select_one(".card-text.text-muted, p.card-text")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        footer = card.get_text(" ", strip=True)
        city = "Pakistan"
        # City sits next to the "N days left" badge — stop before "View Details"
        m_city = re.search(
            r"City\s*:\s*([A-Za-z][A-Za-z \-]{0,40}?)(?:\s*View Details|\s*$)",
            footer,
            flags=re.I,
        )
        if m_city:
            city = m_city.group(1).strip(" -")

        days_left: Optional[int] = None
        m_days = re.search(r"(\d+)\s*days?\s*left", footer, flags=re.I)
        if m_days:
            days_left = int(m_days.group(1))

        link_el = card.select_one("a[href*='tn.php']")
        if not link_el or not link_el.get("href"):
            continue
        link = urljoin(BASE + "/", link_el["href"])

        blob = f"{title} {description}"
        if require_theme and not _has_theme(blob):
            continue

        deadline = (
            _deadline_from_days_left(days_left) if days_left is not None else None
        )

        # Tender number often appears as #48875 in the title
        tender_no = None
        m_no = re.search(r"#(\d+)", title)
        if m_no:
            tender_no = m_no.group(1)

        items.append(
            {
                "title": title[:220],
                "description": description[:600] or title,
                "link": link,
                "city": city,
                "days_left": days_left,
                "deadline": deadline,
                "tender_no": tender_no,
            }
        )
    return items


def _enrich_closing_date(item: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch detail page once to replace approximate deadline with Closing Date."""
    html = _fetch_html(item["link"])
    if not html:
        return item
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    closing = _parse_closing_date(text)
    if closing:
        item["deadline"] = closing
        item["deadline_display"] = closing
    # Prefer longer description from detail if listing was truncated
    m_desc = re.search(
        r"Description\s+(.+?)(?:\d+\s*days?\s*left|Closing\s*Date|City\b)",
        text,
        flags=re.I | re.S,
    )
    if m_desc:
        full = " ".join(m_desc.group(1).split())
        if len(full) > len(item.get("description") or ""):
            item["description"] = full[:900]
            item["content"] = full[:2000]
    return item


def _to_opportunity(
    raw: Dict[str, Any], feed_config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    link = raw.get("link") or ""
    title = raw.get("title") or ""
    if not link or not title:
        return None

    deadline = raw.get("deadline")
    today = datetime.now(timezone.utc).date().isoformat()
    if deadline and deadline < today:
        return None

    city = raw.get("city") or "Pakistan"
    desc = raw.get("description") or title
    content = raw.get("content") or desc
    days = raw.get("days_left")
    deadline_display = raw.get("deadline_display") or deadline or (
        f"{days} days left" if days is not None else "Not specified"
    )

    return {
        "id": _id(link),
        "title": title,
        "link": link,
        "description": desc,
        "content": content,
        "pubDate": datetime.now(timezone.utc).isoformat(),
        "deadline": deadline,
        "deadline_display": deadline_display,
        "author": feed_config.get("name") or "My Tender Notice",
        "categories": ["Tender", "Pakistan", city],
        "country": "Pakistan",
        "location": city,
        "opportunity_type": "Tender",
        "content_kind": "opportunity",
        "source": {
            "id": feed_config.get("id"),
            "name": feed_config.get("name"),
            "url": feed_config.get("url") or INDEX_URL,
        },
        "tender_no": raw.get("tender_no"),
        "days_remaining": str(days) if days is not None else None,
    }


async def scrape_mytendernotice(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scrape My Tender Notice active / climate-relevant tenders.

    What: homepage + selected categories → structured Tender opportunities.
    Why: expand Pakistan apply-able procurement coverage beyond PakTender.
    """
    name = url_config.get("name") or "My Tender Notice"
    print(f"Fetching My Tender Notice: {name}")

    collected: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()

    # 1) Homepage — latest active (no theme gate; already "active")
    index_html = _fetch_html(url_config.get("url") or INDEX_URL)
    if index_html:
        for raw in _parse_cards(index_html, require_theme=False):
            if raw["link"] in seen_links:
                continue
            seen_links.add(raw["link"])
            collected.append(raw)
        print(f"  Homepage: {len(collected)} active card(s)")
    else:
        print("  Homepage fetch failed")

    # 2) Climate-leaning categories
    for cat in CLIMATE_CATEGORIES:
        cat_url = f"{BASE}/category.php?category={cat}"
        html = _fetch_html(cat_url)
        if not html:
            continue
        # Broad categories need a theme keyword; solar/water/sanitation keep all
        broad = cat.startswith(
            ("electrical-", "construction-", "consultancy-")
        )
        rows = _parse_cards(html, require_theme=broad)
        kept = 0
        for raw in rows:
            if raw["link"] in seen_links:
                continue
            # Prefer cards that still show days left (active)
            if raw.get("days_left") is None:
                continue
            seen_links.add(raw["link"])
            collected.append(raw)
            kept += 1
            if kept >= MAX_PER_CATEGORY:
                break
        print(f"  Category {cat}: +{kept}")

    # 3) Enrich a subset with exact Closing Date from detail pages
    enrich_n = min(len(collected), MAX_DETAIL_FETCHES)
    for i in range(enrich_n):
        collected[i] = _enrich_closing_date(collected[i])

    # 4) Build opportunity records; drop expired
    out: List[Dict[str, Any]] = []
    for raw in collected:
        item = _to_opportunity(raw, url_config)
        if item:
            out.append(item)

    print(f"[OK] {name}: {len(out)} open tender(s)")
    return out
