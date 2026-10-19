"""
Islamic Development Bank (IsDB) project procurement — apply-able notices.

Why: Planetive has offices in Pakistan + UAE; IsDB posts EOIs / RFPs /
consulting notices firms can bid on. Country taxonomy pages are
server-rendered HTML (no API), so we scrape those listings.

Scope (Phase 1): Pakistan + United Arab Emirates only.
Skip Closed and Contract Award notices.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from services.content_filter import passes_content_filters

BASE = "https://www.isdb.org"
# Official country taxonomy term IDs on isdb.org project-procurement
PAKISTAN_TERM = 22
UAE_TERM = 101
ACTIVE_TERM = 204  # all Active notices — we keep only PK/UAE rows

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

FOCUS_COUNTRY_MARKERS = (
    "pakistan",
    "uae",
    "united arab emirates",
    "dubai",
    "abu dhabi",
)


def _item_id(link: str) -> str:
    return hashlib.md5((link or "").encode()).hexdigest()[:50]


def _parse_deadline(text: str) -> Optional[str]:
    """Parse dates like '29 October 2026' → ISO date string."""
    if not text:
        return None
    text = " ".join(str(text).split())
    try:
        from dateutil import parser as date_parser

        dt = date_parser.parse(text, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.date().isoformat()
    except Exception:
        return None


def _normalize_country(raw: str) -> str:
    t = (raw or "").strip()
    low = t.lower()
    if "pakistan" in low:
        return "Pakistan"
    if "emirates" in low or low == "uae" or "dubai" in low or "abu dhabi" in low:
        return "United Arab Emirates"
    return t or "Not specified"


def _is_focus_country(country: str, blob: str) -> bool:
    hay = f"{country} {blob}".lower()
    return any(m in hay for m in FOCUS_COUNTRY_MARKERS)


def _map_opportunity_type(notice_type: str, title: str) -> str:
    blob = f"{notice_type} {title}".lower()
    if "contract award" in blob:
        return "Tender"
    if (
        "expression of interest" in blob
        or "eoi" in blob
        or "reoi" in blob
        or "request for proposal" in blob
        or "rfp" in blob
        or "consult" in blob
    ):
        return "RFP"
    if "grant" in blob or "funding" in blob:
        return "Grant"
    if "general procurement notice" in blob or "gpn" in blob:
        return "Tender"
    return "Tender"


def _should_skip(status: str, notice_type: str, title: str) -> bool:
    blob = f"{status} {notice_type} {title}".lower()
    if "closed" in blob:
        return True
    if "contract award" in blob or "attribution" in blob:
        return True
    return False


_KNOWN_COUNTRIES = (
    "pakistan",
    "united arab emirates",
    "uae",
    "saudi arabia",
    "bangladesh",
    "nigeria",
    "lebanon",
    "egypt",
    "jordan",
    "morocco",
    "tunisia",
    "turkey",
    "türkiye",
    "indonesia",
    "uzbekistan",
    "kazakhstan",
    "azerbaijan",
    "senegal",
    "uganda",
    "guinea",
    "oman",
    "bahrain",
    "qatar",
    "kuwait",
    "iraq",
    "yemen",
    "sudan",
    "somalia",
    "djibouti",
    "maldives",
    "afghanistan",
    "palestine",
    "gambia",
    "benin",
    "togo",
    "chad",
    "mali",
    "niger",
    "cameroon",
    "albania",
    "suriname",
    "guyana",
    "mozambique",
    "sierra leone",
    "mauritania",
    "libya",
    "algeria",
    "iran",
    "kyrgyz",
    "tajikistan",
    "turkmenistan",
    "cote d'ivoire",
    "côte d'ivoire",
)

_NOTICE_TYPE_KEYS = (
    "expression of interest",
    "specific procurement notice",
    "general procurement notice",
    "contract award",
    "pre-qualification",
    "prequalification",
    "request for proposal",
    "request for expressions of interest",
)


def _extract_country_from_parts(parts: List[str], default_country: str = "") -> str:
    for p in parts:
        pl = p.lower().strip()
        if re.search(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", p):
            continue
        if pl in ("active", "closed") or pl.startswith("closed"):
            continue
        if any(k in pl for k in _NOTICE_TYPE_KEYS):
            continue
        if any(c in pl for c in _KNOWN_COUNTRIES):
            return p.strip()
    return default_country


def parse_isdb_listing_html(
    html: str, default_country: str = ""
) -> List[Dict[str, Any]]:
    """Extract notice cards from an IsDB taxonomy / Active listing page."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select(".views-row")
    items: List[Dict[str, Any]] = []

    for row in rows:
        a = row.find("a", href=True)
        if not a:
            continue
        href = a["href"].strip()
        if "/project-procurement/tenders/" not in href:
            continue
        link = urljoin(BASE, href)
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title or len(title) < 8:
            h = row.find(["h2", "h3"])
            title = " ".join((h.get_text(" ", strip=True) if h else "").split())
        if not title:
            continue

        raw = " ".join(row.get_text(" ", strip=True).split())
        parts = [p.strip() for p in row.get_text(" | ", strip=True).split("|") if p.strip()]

        status = ""
        notice_type = ""
        for p in parts:
            pl = p.lower()
            if pl == "active" or pl == "closed" or pl.startswith("closed"):
                status = p
            elif any(k in pl for k in _NOTICE_TYPE_KEYS):
                notice_type = p

        date_match = re.search(
            r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|"
            r"August|September|October|November|December)\s+\d{4})\b",
            raw,
            flags=re.I,
        )
        deadline_raw = date_match.group(1) if date_match else ""

        country = _extract_country_from_parts(parts, default_country="")
        if _should_skip(status, notice_type, title):
            continue

        # On a country taxonomy page: keep if listed country is focus, OR
        # country missing (then trust the page default). Drop wrong countries
        # that sometimes appear on the UAE page (misc awards).
        if country:
            country_n = _normalize_country(country)
            if not _is_focus_country(country_n, country_n):
                continue
        elif default_country:
            country_n = _normalize_country(default_country)
        else:
            country_n = "Not specified"
            if not _is_focus_country(country_n, f"{title} {raw}"):
                continue

        deadline = _parse_deadline(deadline_raw)
        opp_type = _map_opportunity_type(notice_type, title)
        description = (
            f"{notice_type or 'Procurement notice'}. "
            f"Country: {country_n}. "
            f"Deadline: {deadline or deadline_raw or 'Not specified'}."
        )

        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "content": raw[:2000],
                "pubDate": datetime.now(timezone.utc).isoformat(),
                "deadline": deadline,
                "deadline_display": deadline_raw or deadline or "Not specified",
                "author": "Islamic Development Bank",
                "categories": [
                    c
                    for c in [
                        "IsDB",
                        country_n,
                        notice_type or "Procurement",
                        opp_type,
                    ]
                    if c
                ],
                "country": country_n,
                "location": country_n,
                "opportunity_type": opp_type,
                "content_kind": "opportunity",
            }
        )

    return items


async def _fetch_pages(
    term_id: int, max_pages: int, label: str, default_country: str
) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    async with httpx.AsyncClient(
        headers=HEADERS, timeout=40.0, follow_redirects=True, verify=True
    ) as client:
        for page in range(0, max_pages):
            url = f"{BASE}/project-procurement/taxonomy/term/{term_id}"
            if page > 0:
                url = f"{url}?page={page}"
            print(f"  IsDB {label} page {page}: {url}")
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except Exception as e:
                print(f"    ✗ fetch failed: {e}")
                break

            page_items = parse_isdb_listing_html(
                resp.text, default_country=default_country
            )
            if not page_items:
                print("    (no matching open notices on this page)")
                if page > 0:
                    break
                continue

            added = 0
            for item in page_items:
                link = item["link"]
                if link in seen:
                    continue
                seen.add(link)
                collected.append(item)
                added += 1
            print(f"    kept {added} (running total {len(collected)})")
            if added == 0 and page > 0:
                break

    return collected


async def scrape_isdb_procurement(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scrape IsDB Pakistan + UAE taxonomy listings → app opportunity items.
    """
    max_pages = int(url_config.get("max_pages", 5))
    print(f"Fetching IsDB procurement (Pakistan + UAE, max {max_pages} pages each)...")

    raw: List[Dict[str, Any]] = []
    raw.extend(
        await _fetch_pages(PAKISTAN_TERM, max_pages, "Pakistan", "Pakistan")
    )
    raw.extend(
        await _fetch_pages(UAE_TERM, max_pages, "UAE", "United Arab Emirates")
    )
    # Catch Active notices tagged PK/UAE that country pages may miss
    raw.extend(await _fetch_pages(ACTIVE_TERM, max_pages, "Active", ""))

    # Stamp source + ids
    out: List[Dict[str, Any]] = []
    for item in raw:
        link = item.get("link") or ""
        item["id"] = _item_id(link)
        item["source"] = {
            "id": url_config.get("id", "isdb-procurement"),
            "name": url_config.get("name", "IsDB - Project Procurement"),
            "url": url_config.get("url", f"{BASE}/project-procurement/tenders"),
        }
        out.append(item)

    # Geography already enforced; apply ESG theme unless skipped
    keywords = url_config.get("keywords") or []
    skip_kw = bool(url_config.get("skip_keyword_filter"))
    filtered = [
        i
        for i in out
        if passes_content_filters(i, keywords, skip_keyword_filter=skip_kw)
    ]
    print(f"[OK] IsDB: {len(filtered)}/{len(out)} after theme filter")
    return filtered
