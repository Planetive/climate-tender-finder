"""
Enrich ADB tender RSS items with real bid deadlines.

Why: ADB FeedBurner only includes "Date: YYYY-MM-DD" (posted/invitation date)
and "Status: Active". The actual "Deadline for Submission of Bids" is on the
linked IFB page/PDF — so the UI was showing April while the tender had already closed.

Approach: follow the item link; if PDF, extract text with pypdf; parse deadline;
set item['deadline']. Caller should drop past deadlines.
"""
import re
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

_DEADLINE_PATTERNS = [
    r"Deadline\s+for\s+Submission\s+of\s+Bids\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    r"deadline\s*[:\-]\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    r"Submission\s+of\s+Bids\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    r"Closing\s+Date\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    r"Bid\s+Closing\s*(?:Date)?\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    r"Bids?\s+(?:must|should)\s+be\s+(?:received|submitted)[^\d]{0,40}(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html,application/xhtml+xml,*/*",
}


def _parse_day_month_year(raw: str) -> Optional[str]:
    """Convert '11 May 2026' → '2026-05-11'."""
    raw = re.sub(r"\s+", " ", (raw or "").strip())
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def extract_deadline_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    compact = re.sub(r"[ \t]+", " ", text)
    for pat in _DEADLINE_PATTERNS:
        m = re.search(pat, compact, flags=re.IGNORECASE)
        if not m:
            continue
        iso = _parse_day_month_year(m.group(1))
        if iso:
            return iso
    return None


def extract_deadline_from_pdf_bytes(data: bytes) -> Optional[str]:
    try:
        from pypdf import PdfReader
        from io import BytesIO
    except ImportError:
        print("⚠ pypdf not installed — cannot read ADB IFB PDFs for deadlines")
        return None

    try:
        reader = PdfReader(BytesIO(data))
        # First few pages usually hold the invitation summary
        chunks = []
        for page in reader.pages[:6]:
            chunks.append(page.extract_text() or "")
        return extract_deadline_from_text("\n".join(chunks))
    except Exception as e:
        print(f"⚠ ADB PDF parse error: {e}")
        return None


def extract_deadline_from_html(html: str) -> Optional[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    found = extract_deadline_from_text(text)
    if found:
        return found

    # Drupal-style label + value
    for lab in soup.select(".field__label, .field-label, dt, th"):
        label = lab.get_text(" ", strip=True).lower()
        if not any(k in label for k in ("deadline", "closing", "submission")):
            continue
        sib = lab.find_next(["div", "dd", "td", "span", "time"])
        if not sib:
            continue
        val = sib.get_text(" ", strip=True)
        # Try ISO first
        m = re.search(r"(\d{4}-\d{2}-\d{2})", val)
        if m:
            return m.group(1)
        m2 = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", val)
        if m2:
            iso = _parse_day_month_year(m2.group(1))
            if iso:
                return iso
    return None


async def enrich_adb_deadline(item: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
    """
    Follow ADB item link and set deadline when found.
    Does not guess — leaves deadline unset if extraction fails.
    """
    link = (item.get("link") or "").strip()
    if not link or "adb.org" not in link.lower():
        return item
    # Already have a structured deadline
    if item.get("deadline") and re.match(r"^\d{4}-\d{2}-\d{2}", str(item["deadline"])):
        return item

    try:
        response = await client.get(link)
        response.raise_for_status()
        ctype = (response.headers.get("content-type") or "").lower()
        final_url = str(response.url)

        deadline = None
        if "pdf" in ctype or final_url.lower().endswith(".pdf"):
            deadline = extract_deadline_from_pdf_bytes(response.content)
        else:
            deadline = extract_deadline_from_html(response.text)

        if deadline:
            item["deadline"] = deadline
            # Keep RSS Date as posted if present
            if not item.get("posted") and item.get("pubDate"):
                item["posted"] = str(item["pubDate"])[:10]
    except Exception as e:
        print(f"  ⚠ ADB enrich failed for {link[:80]}: {e}")

    return item


def is_deadline_past(item: Dict[str, Any], today: Optional[str] = None) -> bool:
    """True when item has a parseable deadline strictly before today (UTC date)."""
    today = today or datetime.utcnow().strftime("%Y-%m-%d")
    raw = (item.get("deadline") or "")[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return False
    return raw < today


def _iso_date_prefix(value: Any) -> Optional[str]:
    """Pull YYYY-MM-DD from posted / pubDate / ISO strings. No guessing."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    # "2016-04-25" or "2016-04-25T00:00:00"
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    return None


def item_posted_iso(item: Dict[str, Any]) -> Optional[str]:
    """Best-known posted/invitation date for an item (ADB Date: field or pubDate)."""
    for key in ("posted", "pubDate", "pub_date"):
        iso = _iso_date_prefix(item.get(key))
        if iso:
            return iso
    return None


def has_open_deadline(item: Dict[str, Any], today: Optional[str] = None) -> bool:
    """True when deadline exists and is today or later."""
    today = today or datetime.utcnow().strftime("%Y-%m-%d")
    raw = (item.get("deadline") or "")[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return False
    return raw >= today


def is_stale_posted(
    item: Dict[str, Any],
    max_age_days: int = 365,
    today: Optional[str] = None,
) -> bool:
    """
    True when the notice is too old to be actionable.

    Rules (simple, no guessing):
    - Past bid deadline → stale (same as is_deadline_past)
    - Open/future deadline → keep, even if posted long ago
    - No deadline + posted older than max_age_days → stale
      (ADB Advance Notices keep Status: Active for years; posted 2012–2016
      must not clutter the Opportunities list)

    If posted date is missing, we do NOT mark stale (avoid deleting unknowns).
    """
    today = today or datetime.utcnow().strftime("%Y-%m-%d")
    if is_deadline_past(item, today=today):
        return True
    if has_open_deadline(item, today=today):
        return False

    posted = item_posted_iso(item)
    if not posted:
        return False

    try:
        posted_dt = datetime.strptime(posted, "%Y-%m-%d")
        today_dt = datetime.strptime(today, "%Y-%m-%d")
    except ValueError:
        return False

    age_days = (today_dt - posted_dt).days
    return age_days > max_age_days


async def enrich_adb_items(items: list, max_items: int = 40) -> list:
    """Enrich up to max_items ADB links (keeps ingest time reasonable)."""
    if not items:
        return items

    timeout = httpx.Timeout(45.0, connect=15.0)
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers=_HEADERS,
        verify=False,
    ) as client:
        out = []
        for idx, item in enumerate(items):
            if idx < max_items:
                item = await enrich_adb_deadline(item, client)
            out.append(item)
        return out
