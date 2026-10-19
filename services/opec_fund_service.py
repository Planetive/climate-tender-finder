"""
OPEC Fund procurement — apply-able consulting + project notices.

Why: Planetive (PK + UAE) can bid on OPEC Fund REOIs/RFPs.
- Project procurement: keep Pakistan + UAE only
- Corporate consultants page: HQ REOIs open to international firms (apply from UAE/PK)
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

BASE = "https://opecfund.org"
PROJECT_URL = f"{BASE}/work-with-us/project-procurement/current-opportunities"
CONSULTANTS_URL = f"{BASE}/work-with-us/consultants/current-opportunities"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
}

FOCUS_COUNTRY = (
    "pakistan",
    "uae",
    "united arab emirates",
    "dubai",
    "abu dhabi",
)


def _id(link: str) -> str:
    return hashlib.md5((link or "").encode()).hexdigest()[:50]


def _parse_date(text: str) -> Optional[str]:
    if not text or text.strip().lower() in ("n/a", "na", "-"):
        return None
    try:
        from dateutil import parser as date_parser

        dt = date_parser.parse(text, fuzzy=True)
        return dt.date().isoformat()
    except Exception:
        return None


def _is_past(deadline_iso: Optional[str]) -> bool:
    if not deadline_iso:
        return False
    try:
        return datetime.strptime(deadline_iso, "%Y-%m-%d").date() < datetime.now(
            timezone.utc
        ).date()
    except Exception:
        return False


def _map_type(notice_type: str, title: str) -> str:
    blob = f"{notice_type} {title}".lower()
    if "reoi" in blob or "expression of interest" in blob or "eoi" in blob:
        return "RFP"
    if "rfp" in blob or "request for proposal" in blob:
        return "RFP"
    if "grant" in blob:
        return "Grant"
    return "Tender"


def _row_link(tr, fallback: str) -> str:
    a = tr.find("a", href=True)
    if a and a.get("href"):
        return urljoin(BASE, a["href"].strip())
    return fallback


def parse_project_table(html: str) -> List[Dict[str, Any]]:
    """Date | Country | Project/Notice | Sector | Closing Date | Type"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    items: List[Dict[str, Any]] = []
    for tr in table.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
        if len(cells) < 5:
            continue
        posted_raw, country, title, sector = cells[0], cells[1], cells[2], cells[3]
        closing_raw = cells[4] if len(cells) > 4 else ""
        notice_type = cells[5] if len(cells) > 5 else ""
        title = re.sub(r"\s*Downloads?:.*$", "", title, flags=re.I).strip()
        title = re.sub(r"\s+Download\s*$", "", title, flags=re.I).strip()
        if not title or len(title) < 12:
            continue
        country_l = (country or "").lower()
        if not any(m in country_l for m in FOCUS_COUNTRY):
            continue
        deadline = _parse_date(closing_raw)
        if not deadline or _is_past(deadline):
            continue
        link = _row_link(tr, PROJECT_URL)
        country_n = "Pakistan" if "pakistan" in country_l else "United Arab Emirates"
        opp_type = _map_type(notice_type, title)
        items.append(
            {
                "title": title[:300],
                "link": link,
                "description": (
                    f"{notice_type or 'Procurement notice'}. Sector: {sector or 'Not specified'}. "
                    f"Country: {country_n}. Deadline: {deadline or closing_raw or 'Not specified'}."
                ),
                "content": " | ".join(cells),
                "pubDate": _parse_date(posted_raw) or datetime.now(timezone.utc).isoformat(),
                "deadline": deadline,
                "deadline_display": closing_raw or deadline or "Not specified",
                "author": "OPEC Fund",
                "categories": ["OPEC Fund", country_n, sector or "Procurement", opp_type],
                "country": country_n,
                "location": country_n,
                "opportunity_type": opp_type,
                "content_kind": "opportunity",
            }
        )
    return items


def parse_consultants_table(html: str) -> List[Dict[str, Any]]:
    """Description | Posting date | Deadline — HQ consulting REOIs (international)."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    items: List[Dict[str, Any]] = []
    for tr in table.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
        if len(cells) < 2:
            continue
        title = cells[0]
        posted_raw = cells[1] if len(cells) > 1 else ""
        closing_raw = cells[2] if len(cells) > 2 else ""
        if not title or len(title) < 8:
            continue
        # Drop "Submit REOI here" noise from title text
        title = re.sub(r"\s*Submit REOI here\s*", " ", title, flags=re.I).strip()
        deadline = _parse_date(closing_raw)
        if _is_past(deadline):
            continue
        link = _row_link(tr, CONSULTANTS_URL)
        opp_type = _map_type(title, title)
        items.append(
            {
                "title": title[:300],
                "link": link,
                "description": (
                    f"OPEC Fund consulting REOI (HQ). "
                    f"Deadline: {deadline or closing_raw or 'Not specified'}."
                ),
                "content": " | ".join(cells),
                "pubDate": _parse_date(posted_raw) or datetime.now(timezone.utc).isoformat(),
                "deadline": deadline,
                "deadline_display": closing_raw or deadline or "Not specified",
                "author": "OPEC Fund",
                "categories": ["OPEC Fund", "Consulting", "International", opp_type],
                "country": "International",
                "location": "International (OPEC Fund HQ)",
                "opportunity_type": opp_type,
                "content_kind": "opportunity",
            }
        )
    return items


async def scrape_opec_fund(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    print("Fetching OPEC Fund project + consultant opportunities...")
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(
        headers=HEADERS, timeout=45.0, follow_redirects=True
    ) as client:
        for label, url, parser in (
            ("project", PROJECT_URL, parse_project_table),
            ("consultants", CONSULTANTS_URL, parse_consultants_table),
        ):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                rows = parser(resp.text)
                print(f"  OPEC {label}: {len(rows)} kept")
            except Exception as e:
                print(f"  ✗ OPEC {label} failed: {e}")
                continue
            for item in rows:
                link = item.get("link") or ""
                if link in seen:
                    continue
                seen.add(link)
                item["id"] = _id(link + (item.get("title") or ""))
                item["source"] = {
                    "id": url_config.get("id", "opec-fund-procurement"),
                    "name": url_config.get("name", "OPEC Fund - Procurement"),
                    "url": url_config.get("url", PROJECT_URL),
                }
                out.append(item)

    print(f"[OK] OPEC Fund: {len(out)} opportunities")
    return out
