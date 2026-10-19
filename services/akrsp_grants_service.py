"""
Aga Khan Rural Support Programme (AKRSP) — Pakistan climate/community grants.

Listing: https://akrsp.org.pk/grants-funding-opportunities/
Why: open micro-grant / CSO calls Planetive or partners in Pakistan can apply to
(or support clients to apply).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

LIST_URL = "https://akrsp.org.pk/grants-funding-opportunities/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def _id(link: str) -> str:
    return hashlib.md5((link or "").encode()).hexdigest()[:50]


def _parse_deadline(text: str) -> Optional[str]:
    if not text:
        return None
    # Formats: 20/08/2026, 20 August 2026
    m = re.search(
        r"(?:Last Date to Apply|Deadline|Application Deadline)\s*[:\-]?\s*"
        r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        text,
        flags=re.I,
    )
    raw = m.group(1) if m else None
    if not raw:
        m2 = re.search(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", text)
        raw = m2.group(1) if m2 else None
    if not raw:
        return None
    try:
        from dateutil import parser as date_parser

        return date_parser.parse(raw, dayfirst=True, fuzzy=True).date().isoformat()
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


def parse_akrsp_listing(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "grants-funding-opp" not in href:
            continue
        if href.rstrip("/").endswith("grants-funding-opportunities"):
            continue
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title or title.lower() in ("details", "read more", "apply"):
            continue
        if "grants & funding opportunities" in title.lower():
            continue
        if len(title) < 12:
            continue
        link = urljoin(LIST_URL, href)
        if link in seen:
            continue
        seen.add(link)

        # Nearby text for deadline / location
        parent = a
        blob = ""
        for _ in range(6):
            if parent is None:
                break
            blob = parent.get_text(" ", strip=True)
            if "Last Date" in blob or "Apply" in blob or re.search(r"\d{1,2}/\d{1,2}/\d{4}", blob):
                break
            parent = parent.parent

        deadline = _parse_deadline(blob)
        if _is_past(deadline):
            continue

        items.append(
            {
                "title": title[:300],
                "link": link,
                "description": (
                    f"AKRSP grant / funding call (Pakistan). "
                    f"Deadline: {deadline or 'Not specified'}."
                ),
                "content": blob[:2000],
                "pubDate": datetime.now(timezone.utc).isoformat(),
                "deadline": deadline,
                "deadline_display": deadline or "Not specified",
                "author": "AKRSP",
                "categories": ["AKRSP", "Pakistan", "Grant", "Climate"],
                "country": "Pakistan",
                "location": "Pakistan",
                "opportunity_type": "Grant",
                "content_kind": "opportunity",
            }
        )

    return items


def _fetch_list_html() -> Optional[str]:
    """Prefer requests (AKRSP often 403s bare httpx)."""
    try:
        import requests

        resp = requests.get(LIST_URL, headers=HEADERS, timeout=40)
        if resp.status_code == 200 and resp.text.strip():
            return resp.text
        print(f"  AKRSP requests status {resp.status_code}")
    except Exception as e:
        print(f"  AKRSP requests failed: {e}")
    return None


async def scrape_akrsp_grants(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    print("Fetching AKRSP grants & funding opportunities...")
    import asyncio

    html = await asyncio.get_event_loop().run_in_executor(None, _fetch_list_html)
    if not html:
        # Fallback httpx
        try:
            async with httpx.AsyncClient(
                headers=HEADERS, timeout=40.0, follow_redirects=True
            ) as client:
                resp = await client.get(LIST_URL)
                resp.raise_for_status()
                html = resp.text
        except Exception as e:
            print(f"  AKRSP list failed: {e}")
            return []

    rows = parse_akrsp_listing(html)
    out: List[Dict[str, Any]] = []
    for item in rows:
        item["id"] = _id(item.get("link") or item.get("title") or "")
        item["source"] = {
            "id": url_config.get("id", "akrsp-grants"),
            "name": url_config.get("name", "AKRSP - Grants & Funding"),
            "url": url_config.get("url", LIST_URL),
        }
        out.append(item)

    print(f"[OK] AKRSP: {len(out)} open grant calls")
    return out
