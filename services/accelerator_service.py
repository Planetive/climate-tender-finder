"""
Climate / cleantech accelerator program pages (PK + UAE).

Each feed config points at one program URL. We fetch the page, pull a
deadline if present, and store one Accelerator opportunity when the
program looks open (future deadline, or explicit "applications open" /
rolling language even after a cohort deadline).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

OPEN_PHRASES = (
    "applications are now open",
    "applications open",
    "currently accepting applications",
    "accepting applications",
    "apply now",
    "rolling basis",
    "reviewed on a rolling basis",
    "do not have a set deadline",
    "applications do not close",
    "next cohort is coming",
    "seats left",
)

CLOSED_PHRASES = (
    "applications are closed",
    "applications closed",
    "applications for cfa",  # CFA country pages say "Applications for CFA X are now closed"
    "this call has now closed",
    "no longer accepting",
    "deadline has passed",
    "are now closed",
)

# Used when feed sets require_climate_theme=True (e.g. broad NIC / Ignite)
CLIMATE_THEME_MARKERS = (
    "climate",
    "cleantech",
    "clean tech",
    "clean energy",
    "renewable",
    "solar",
    "esg",
    "sustainab",
    "carbon",
    "net zero",
    "green tech",
    "greentech",
    "circular",
    "environment",
)


def _id(link: str) -> str:
    return hashlib.md5((link or "").encode()).hexdigest()[:50]


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def _parse_deadlines(text: str) -> List[str]:
    """Return ISO dates found near deadline / applications-close wording."""
    found: List[str] = []
    patterns = [
        r"(?:deadline|applications?\s+close|closes?|apply\s+by|due)\s*(?:is|:)?\s*"
        r"(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})",
        r"(?:deadline|applications?\s+close|closes?)\s*(?:is|:)?\s*"
        r"([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"Applications?\s+close\s+(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})",
        r"current deadline is\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    ]
    try:
        from dateutil import parser as date_parser
    except Exception:
        return found

    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            try:
                iso = date_parser.parse(m.group(1), fuzzy=True).date().isoformat()
                if iso not in found:
                    found.append(iso)
            except Exception:
                continue
    return found


def _best_deadline(dates: List[str]) -> Optional[str]:
    if not dates:
        return None
    # Prefer the soonest future date; else latest past (for messaging)
    today = datetime.now(timezone.utc).date().isoformat()
    future = sorted(d for d in dates if d >= today)
    if future:
        return future[0]
    return sorted(dates)[-1]


def _has_climate_theme(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in CLIMATE_THEME_MARKERS)


def _next_call_hint(text: str) -> Optional[str]:
    """Pull 'next call … late 2026/early 2027' style hints from closed pages."""
    m = re.search(
        r"next call[^.]*?(late\s+20\d{2}\s*/\s*early\s+20\d{2}|20\d{2})",
        text or "",
        flags=re.I,
    )
    if m:
        return " ".join(m.group(0).split())
    return None


def _is_open(
    text: str,
    deadline_iso: Optional[str],
    force_open: bool = False,
    keep_when_closed: bool = False,
) -> Tuple[bool, str]:
    low = text.lower()
    looks_closed = any(p in low for p in CLOSED_PHRASES) and not any(
        p in low for p in OPEN_PHRASES if p != "cohort"
    )
    # "rolling basis" / "apply now" beat closed wording
    if looks_closed and any(
        p in low
        for p in (
            "applications are now open",
            "currently accepting applications",
            "rolling basis",
        )
    ):
        looks_closed = False

    if looks_closed:
        if keep_when_closed or force_open:
            return True, "watch_next_call"
        return False, "closed"

    today = datetime.now(timezone.utc).date().isoformat()
    if deadline_iso and deadline_iso >= today:
        return True, "deadline_open"

    if any(p in low for p in OPEN_PHRASES) or force_open:
        # Past cohort deadline but still accepting / rolling → keep
        return True, "rolling_or_open"

    if deadline_iso and deadline_iso < today:
        if keep_when_closed:
            return True, "watch_next_call"
        return False, "deadline_passed"

    # No deadline + no clear open signal → skip (avoid stale pages)
    if force_open or keep_when_closed:
        return True, "rolling_or_open"
    return False, "unclear"


def build_accelerator_item(
    html: str, feed_config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    text = _clean_text(html)
    if len(text) < 80:
        return None

    # Broad tech portals (NIC/Ignite): only keep if climate/ESG language is present
    if feed_config.get("require_climate_theme") and not _has_climate_theme(text):
        print(
            f"  Accelerator skip (no climate/ESG theme): {feed_config.get('name')}"
        )
        return None

    dates = _parse_deadlines(text)
    deadline = _best_deadline(dates)
    force_open = bool(feed_config.get("force_open"))
    keep_when_closed = bool(feed_config.get("keep_when_closed"))
    open_ok, reason = _is_open(
        text,
        deadline,
        force_open=force_open,
        keep_when_closed=keep_when_closed,
    )
    if not open_ok:
        print(f"  Accelerator skip ({reason}): {feed_config.get('name')}")
        return None

    country = feed_config.get("country") or "Not specified"
    name = feed_config.get("name") or "Accelerator"
    url = feed_config.get("url") or ""
    title = feed_config.get("opportunity_title") or name
    opp_type = feed_config.get("opportunity_type") or "Accelerator"

    summary_bits = [
        f"{name} — climate/cleantech program.",
        f"Geography: {country}.",
    ]
    next_hint = _next_call_hint(text)
    if reason == "watch_next_call":
        summary_bits.append(
            "Applications are currently closed."
            + (f" {next_hint}." if next_hint else " Watch for the next call.")
        )
    elif deadline:
        if reason == "rolling_or_open":
            summary_bits.append(
                f"Cohort deadline listed as {deadline}; applications still appear open / rolling."
            )
        else:
            summary_bits.append(f"Application deadline: {deadline}.")
    else:
        summary_bits.append("Applications open (rolling / no fixed deadline found).")

    if feed_config.get("require_climate_theme"):
        summary_bits.append(
            "Note: portal is broader tech — prioritize climate/ESG/energy startups."
        )

    # Short excerpt from page (no inventing)
    excerpt = text[:900] + ("…" if len(text) > 900 else "")

    if reason == "watch_next_call":
        deadline_display = next_hint or "Closed — next call TBA"
        deadline_out = None
    elif reason == "deadline_open":
        deadline_display = deadline or "Not specified"
        deadline_out = deadline
    elif reason == "rolling_or_open":
        deadline_display = "Rolling / open"
        deadline_out = None
    else:
        deadline_display = "Not specified"
        deadline_out = None

    return {
        "id": _id(url),
        "title": title,
        "link": url,
        "description": " ".join(summary_bits),
        "content": excerpt,
        "pubDate": datetime.now(timezone.utc).isoformat(),
        "deadline": deadline_out,
        "deadline_display": deadline_display,
        "author": name,
        "categories": [opp_type, "Climate", country],
        "country": country,
        "location": country,
        "opportunity_type": opp_type,
        "content_kind": "opportunity",
        "source": {
            "id": feed_config.get("id"),
            "name": name,
            "url": url,
        },
    }


async def scrape_accelerator_program(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = url_config.get("url") or ""
    name = url_config.get("name") or url_config.get("id") or "accelerator"
    print(f"Fetching accelerator: {name}")
    if not url:
        return []

    html = None
    try:
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=40.0, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        print(f"  httpx failed ({e}), trying requests…")
        try:
            import requests

            resp = requests.get(url, headers=HEADERS, timeout=40)
            if resp.status_code == 200:
                html = resp.text
            else:
                print(f"  requests status {resp.status_code}")
        except Exception as e2:
            print(f"  Accelerator fetch failed: {e2}")
            return []

    if not html:
        return []

    item = build_accelerator_item(html, url_config)
    if not item:
        return []
    print(f"  [OK] {name}: open ({item.get('deadline_display')})")
    return [item]
