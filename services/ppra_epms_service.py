"""
PPRA ePMS — Active Tenders (Pakistan)

Source: https://epms.ppra.gov.pk/public/tenders/active-tenders
Why: official Public Procurement Regulatory Authority active notices with
Closing dates — high-trust Pakistan apply-able tenders.
How: plain HTTP GET with keyword / sector filters → parse table row pairs
(main + detail) → keep open Closing dates.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE = "https://epms.ppra.gov.pk"
LIST_URL = f"{BASE}/public/tenders/active-tenders"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Climate / energy / water focused keyword searches (site search box)
KEYWORD_QUERIES = (
    "solar",
    "water",
    "waste",
    "environment",
    "energy",
    "irrigation",
    "sewage",
    "wastewater",
    "renewable",
    "hydropower",
    "wind",
    "biogas",
    "climate",
)

# Sector IDs from the site's <select name="sector">
# 9 Electrical, 16 Petroleum Oil & Lubricants, 32 LNG/LPG, 6 Civil Works (theme-gated)
SECTOR_QUERIES = (
    {"sector": "9", "require_theme": True},   # Electrical Items
    {"sector": "16", "require_theme": False},  # Petroleum, Oil & Lubricants
    {"sector": "32", "require_theme": False},  # LNG/LPG
    {"sector": "6", "require_theme": True},    # Civil Works — only climate/water-ish
)

THEME_MARKERS = (
    "solar",
    "renewable",
    "energy",
    "power",
    "electric",
    "climate",
    "environment",
    "water",
    "wastewater",
    "sewage",
    "sanitation",
    "irrigation",
    "hydropower",
    "hydro",
    "wind",
    "biogas",
    "carbon",
    "esg",
    "green",
    "sustainab",
    "gas",
    "lng",
    "lpg",
    "pipeline",
    "petroleum",
    "fuel",
    "generator",
    "grid",
    "transformer",
    "waste",
)

MAX_PAGES_PER_QUERY = 3  # 50 per page on the site


def _id(link: str) -> str:
    return hashlib.md5((link or "").encode()).hexdigest()[:50]


def _fetch_html(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[str]:
    try:
        import requests

        resp = requests.get(url, params=params or {}, headers=HEADERS, timeout=60)
        if resp.status_code == 200 and resp.text:
            return resp.text
        print(f"  PPRA ePMS status {resp.status_code} for {params}")
    except Exception as e:
        print(f"  PPRA ePMS fetch failed ({e})")
    return None


def _parse_date(raw: str) -> Optional[str]:
    """Parse 'Dec 24, 2026 02:30 PM' or 'Nov 17, 2026' → ISO date."""
    if not raw:
        return None
    # Drop time portion for date-only ISO
    cleaned = re.sub(r"\d{1,2}:\d{2}\s*(AM|PM)", "", raw, flags=re.I).strip()
    try:
        from dateutil import parser as date_parser

        return date_parser.parse(cleaned, fuzzy=True).date().isoformat()
    except Exception:
        return None


def _has_theme(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in THEME_MARKERS)


def _parse_list_page(html: str, require_theme: bool = False) -> List[Dict[str, Any]]:
    """
    Each tender is two rows: tr.cb-rt-main (summary) + tr.cb-rt-detail (org/meta).
    """
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
    mains = soup.select("tr.cb-rt-main")

    for main in mains:
        detail = main.find_next_sibling("tr", class_="cb-rt-detail")
        tds = main.find_all("td")
        if len(tds) < 7:
            continue

        tender_cell = tds[2].get_text(" ", strip=True)
        m_no = re.search(r"(TS\d+[A-Z]?)", tender_cell, flags=re.I)
        tender_no = m_no.group(1) if m_no else tender_cell.split()[0]

        title = tds[3].get_text(" ", strip=True)
        if not title:
            continue
        # Prefer bold title snippet if present
        strong = tds[3].find(["strong", "b"])
        if strong:
            short = strong.get_text(" ", strip=True)
            if short and len(short) < len(title):
                title = short

        status = tds[4].get_text(" ", strip=True)
        advertised_raw = tds[5].get_text(" ", strip=True)
        closing_raw = tds[6].get_text(" ", strip=True)

        link = None
        for a in main.find_all("a", href=True):
            if "tender-details" in a["href"]:
                link = urljoin(BASE, a["href"])
                break
        if not link and tender_no:
            link = f"{BASE}/public/tenders/tender-details/{tender_no}"

        org = "Not specified"
        city = "Pakistan"
        tender_type = "Tender"
        sector = ""
        detail_text = detail.get_text(" ", strip=True) if detail else ""

        if detail_text:
            m_org = re.search(
                r"Organization\s+(.+?)\s+Tender Type", detail_text, flags=re.I
            )
            if m_org:
                org = " ".join(m_org.group(1).split())
            # Location is usually "... Karachi - Pakistan" at end of org block
            city_matches = re.findall(
                r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\s*-\s*Pakistan\b",
                detail_text,
            )
            if city_matches:
                # Prefer the last short place name (skip long org fragments)
                for cand in reversed(city_matches):
                    words = cand.split()
                    if len(words) <= 2 and len(cand) <= 24:
                        city = cand
                        break
                else:
                    city = city_matches[-1].split()[-1]
            m_type = re.search(
                r"Tender Type\s+(.+?)\s+Procurement Category", detail_text, flags=re.I
            )
            if m_type:
                tender_type = m_type.group(1).strip()
            m_sec = re.search(
                r"Sector\s+(.+?)\s+Tender Nature", detail_text, flags=re.I
            )
            if m_sec:
                sector = m_sec.group(1).strip()

        blob = f"{title} {org} {sector} {detail_text}"
        if require_theme and not _has_theme(blob):
            continue

        deadline = _parse_date(closing_raw)
        advertised = _parse_date(advertised_raw)

        items.append(
            {
                "tender_no": tender_no,
                "title": title[:220],
                "description": title[:600],
                "link": link,
                "status": status,
                "deadline": deadline,
                "deadline_display": closing_raw or deadline or "Not specified",
                "advertised": advertised,
                "author": org,
                "city": city,
                "tender_type": tender_type,
                "sector": sector,
            }
        )
    return items


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

    # Skip cancelled if status says so
    status = (raw.get("status") or "").lower()
    if "cancel" in status:
        return None

    city = raw.get("city") or "Pakistan"
    org = raw.get("author") or feed_config.get("name") or "PPRA ePMS"
    tender_no = raw.get("tender_no") or ""
    sector = raw.get("sector") or ""
    ttype = raw.get("tender_type") or "Tender"

    desc_bits = [
        f"{title}.",
        f"Organization: {org}.",
        f"Location: {city}, Pakistan.",
    ]
    if tender_no:
        desc_bits.append(f"Tender No: {tender_no}.")
    if sector:
        desc_bits.append(f"Sector: {sector}.")
    if ttype:
        desc_bits.append(f"Type: {ttype}.")

    # Map PPRA type labels to our opportunity_type
    opp_type = "Tender"
    low_type = ttype.lower()
    if "rfp" in low_type or "proposal" in low_type:
        opp_type = "RFP"
    elif "eoi" in low_type or "expression" in low_type:
        opp_type = "RFP"

    return {
        "id": _id(link),
        "title": f"{tender_no}: {title}" if tender_no else title,
        "link": link,
        "description": " ".join(desc_bits),
        "content": " ".join(desc_bits),
        "pubDate": raw.get("advertised")
        or datetime.now(timezone.utc).isoformat(),
        "deadline": deadline,
        "deadline_display": raw.get("deadline_display") or deadline or "Not specified",
        "author": org,
        "categories": ["Tender", "Pakistan", city] + ([sector] if sector else []),
        "country": "Pakistan",
        "location": city,
        "opportunity_type": opp_type,
        "content_kind": "opportunity",
        "source": {
            "id": feed_config.get("id"),
            "name": feed_config.get("name"),
            "url": feed_config.get("url") or LIST_URL,
        },
        "tsc_no": tender_no,
        "procurement_agency": org,
        "tender_type": ttype,
    }


def _collect_query(
    params: Dict[str, Any],
    require_theme: bool,
    seen: Set[str],
    max_pages: int,
) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        page_params = dict(params)
        page_params["page"] = page
        html = _fetch_html(LIST_URL, page_params)
        if not html:
            break
        rows = _parse_list_page(html, require_theme=require_theme)
        if not rows:
            break
        new = 0
        for raw in rows:
            key = (raw.get("tender_no") or raw.get("link") or "").upper()
            if not key or key in seen:
                continue
            seen.add(key)
            collected.append(raw)
            new += 1
        # Stop if fewer than a full page (site shows 50/page)
        if len(rows) < 40:
            break
        if new == 0:
            break
    return collected


async def scrape_ppra_epms(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scrape PPRA ePMS active tenders focused on climate/energy/water.

    What: keyword + sector filtered listings with Closing dates.
    Why: official Pakistan procurement feed Planetive can act on.
    """
    name = url_config.get("name") or "PPRA ePMS"
    max_pages = int(url_config.get("max_pages") or MAX_PAGES_PER_QUERY)
    print(f"Fetching PPRA ePMS: {name}")

    seen: Set[str] = set()
    collected: List[Dict[str, Any]] = []

    for kw in KEYWORD_QUERIES:
        rows = _collect_query(
            {"keyword": kw}, require_theme=False, seen=seen, max_pages=max_pages
        )
        if rows:
            print(f"  keyword={kw!r}: +{len(rows)}")
            collected.extend(rows)

    for sec in SECTOR_QUERIES:
        sector_id = sec["sector"]
        require_theme = bool(sec.get("require_theme"))
        rows = _collect_query(
            {"sector": sector_id},
            require_theme=require_theme,
            seen=seen,
            max_pages=max_pages,
        )
        if rows:
            print(f"  sector={sector_id}: +{len(rows)}")
            collected.extend(rows)

    out: List[Dict[str, Any]] = []
    for raw in collected:
        item = _to_opportunity(raw, url_config)
        if item:
            out.append(item)

    print(f"[OK] {name}: {len(out)} open tender(s)")
    return out
