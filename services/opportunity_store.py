"""
Persist opportunities in Supabase (PostgREST) using httpx.

Why: scraped/RSS results used to live only in a 10-minute RAM cache.
Detail pages re-fetched everything and failed even when the list just worked.

Uses SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (service role bypasses RLS).
If env is missing or a call fails, we log and return safely — scraping still works.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

# Known top-level fields stored as columns; everything else goes into `extra`
_COLUMN_KEYS = {
    "id",
    "title",
    "link",
    "description",
    "content",
    "pubDate",
    "deadline",
    "author",
    "categories",
    "source",
    "image",
}


def _supabase_configured() -> bool:
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return bool(url and key)


def _rest_base() -> str:
    return (os.getenv("SUPABASE_URL") or "").rstrip("/") + "/rest/v1"


def _headers(prefer: Optional[str] = None) -> Dict[str, str]:
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def item_to_row(item: Dict[str, Any]) -> Dict[str, Any]:
    """Map a scraper/RSS item dict to an opportunities table row."""
    source = item.get("source") or {}
    if not isinstance(source, dict):
        source = {}

    extra: Dict[str, Any] = {}
    for key, value in item.items():
        if key in _COLUMN_KEYS:
            continue
        if value is None:
            continue
        extra[key] = value

    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(item.get("id") or ""),
        "title": item.get("title") or "",
        "link": item.get("link"),
        "description": item.get("description"),
        "content": item.get("content"),
        "pub_date": item.get("pubDate"),
        "deadline": item.get("deadline"),
        "author": item.get("author"),
        "categories": item.get("categories") if isinstance(item.get("categories"), list) else [],
        "source_id": source.get("id"),
        "source_name": source.get("name"),
        "source_url": source.get("url"),
        "image": item.get("image"),
        "extra": extra,
        "scraped_at": now,
    }


def row_to_item(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a DB row back to the API feed-item shape the frontend expects."""
    extra = row.get("extra") or {}
    if not isinstance(extra, dict):
        extra = {}

    item: Dict[str, Any] = {
        "id": row.get("id"),
        "title": row.get("title") or "",
        "link": row.get("link") or "",
        "description": row.get("description") or "",
        "content": row.get("content") or "",
        "pubDate": row.get("pub_date") or "",
        "deadline": row.get("deadline"),
        "author": row.get("author") or "",
        "categories": row.get("categories") if isinstance(row.get("categories"), list) else [],
        "source": {
            "id": row.get("source_id") or "",
            "name": row.get("source_name") or "",
            "url": row.get("source_url") or "",
        },
        "image": row.get("image"),
    }
    # Merge extras (attachments, country, opportunity_type, etc.)
    for key, value in extra.items():
        if key not in item:
            item[key] = value
    return item


async def upsert_opportunities(items: List[Dict[str, Any]]) -> int:
    """
    Upsert scraped/RSS items into Supabase.
    Returns number of rows sent (0 if skipped/failed).
    """
    if not items:
        return 0
    if not _supabase_configured():
        print("ℹ️  Supabase not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY) — skip persist")
        return 0

    rows = []
    for item in items:
        row = item_to_row(item)
        if not row["id"]:
            continue
        rows.append(row)

    if not rows:
        return 0

    # PostgREST prefers batches; chunk to avoid huge payloads
    chunk_size = 100
    written = 0
    url = f"{_rest_base()}/opportunities"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i : i + chunk_size]
                response = await client.post(
                    url,
                    headers=_headers(prefer="resolution=merge-duplicates,return=minimal"),
                    params={"on_conflict": "id"},
                    json=chunk,
                )
                if response.status_code >= 400:
                    print(
                        f"⚠ Supabase upsert failed ({response.status_code}): "
                        f"{response.text[:300]}"
                    )
                    return written
                written += len(chunk)
        print(f"✓ Persisted {written} opportunities to Supabase")
        return written
    except Exception as e:
        print(f"⚠ Supabase upsert error: {e}")
        return written


async def list_opportunities(
    limit: int = 200,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    List opportunities from Supabase ordered by pub_date (newest first).
    Returns (items, total_count). Empty list if DB unavailable.
    """
    if not _supabase_configured():
        return [], 0

    url = f"{_rest_base()}/opportunities"
    params = {
        "select": "*",
        "order": "pub_date.desc.nullslast,scraped_at.desc",
        "limit": str(limit),
        "offset": str(offset),
    }
    headers = _headers(prefer="count=exact")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code >= 400:
                print(
                    f"⚠ Supabase list failed ({response.status_code}): "
                    f"{response.text[:300]}"
                )
                return [], 0

            rows = response.json()
            if not isinstance(rows, list):
                return [], 0

            # Content-Range: 0-199/1234
            total = len(rows)
            content_range = response.headers.get("content-range") or ""
            if "/" in content_range:
                try:
                    total = int(content_range.split("/")[-1])
                except ValueError:
                    pass

            return [row_to_item(r) for r in rows], total
    except Exception as e:
        print(f"⚠ Supabase list error: {e}")
        return [], 0


async def get_opportunity_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single opportunity by id. Returns None if missing/unavailable."""
    if not item_id or not _supabase_configured():
        return None

    url = f"{_rest_base()}/opportunities"
    params = {
        "select": "*",
        "id": f"eq.{item_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=_headers(), params=params)
            if response.status_code >= 400:
                print(
                    f"⚠ Supabase get-by-id failed ({response.status_code}): "
                    f"{response.text[:300]}"
                )
                return None
            rows = response.json()
            if not isinstance(rows, list) or not rows:
                return None
            return row_to_item(rows[0])
    except Exception as e:
        print(f"⚠ Supabase get-by-id error: {e}")
        return None


async def count_opportunities() -> int:
    """Quick count of stored rows (0 if unavailable)."""
    if not _supabase_configured():
        return 0
    url = f"{_rest_base()}/opportunities"
    params = {"select": "id", "limit": "1"}
    headers = _headers(prefer="count=exact")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.head(url, headers=headers, params=params)
            # Some setups don't support HEAD well; fall back to GET
            if response.status_code >= 400:
                response = await client.get(url, headers=headers, params=params)
            content_range = response.headers.get("content-range") or ""
            if "/" in content_range:
                part = content_range.split("/")[-1]
                if part != "*":
                    return int(part)
            return 0
    except Exception as e:
        print(f"⚠ Supabase count error: {e}")
        return 0


async def count_by_source() -> Dict[str, int]:
    """
    Count stored rows grouped by source_id (for Sources page — no live scrape).
    """
    if not _supabase_configured():
        return {}

    # Fetch source_id only (up to 5000 rows) and count in Python — simple & reliable
    url = f"{_rest_base()}/opportunities"
    params = {
        "select": "source_id",
        "limit": "5000",
    }
    counts: Dict[str, int] = {}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=_headers(), params=params)
            if response.status_code >= 400:
                print(f"⚠ count_by_source failed ({response.status_code}): {response.text[:200]}")
                return {}
            rows = response.json()
            if not isinstance(rows, list):
                return {}
            for row in rows:
                sid = row.get("source_id") or ""
                if not sid:
                    continue
                counts[sid] = counts.get(sid, 0) + 1
            return counts
    except Exception as e:
        print(f"⚠ count_by_source error: {e}")
        return {}


async def delete_old_news(
    news_source_ids: List[str],
    older_than_days: int = 3,
) -> int:
    """
    Delete news rows older than N days. Opportunities (grants/tenders) are NOT deleted.

    Uses source_id list from feed config (content_kind=news).
    Returns approximate deleted count (0 if skipped/failed).
    """
    if not news_source_ids or not _supabase_configured():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    cutoff_iso = cutoff.isoformat()

    # PostgREST: source_id=in.(a,b)&scraped_at=lt.ISO
    ids_csv = ",".join(news_source_ids)
    url = f"{_rest_base()}/opportunities"
    params = {
        "source_id": f"in.({ids_csv})",
        "scraped_at": f"lt.{cutoff_iso}",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Prefer return=representation to count deletions
            response = await client.delete(
                url,
                headers=_headers(prefer="return=representation"),
                params=params,
            )
            if response.status_code >= 400:
                print(
                    f"⚠ Supabase news purge failed ({response.status_code}): "
                    f"{response.text[:300]}"
                )
                return 0
            rows = response.json() if response.content else []
            deleted = len(rows) if isinstance(rows, list) else 0
            print(
                f"✓ Purged {deleted} news items older than {older_than_days} days "
                f"(cutoff {cutoff_iso})"
            )
            return deleted
    except Exception as e:
        print(f"⚠ Supabase news purge error: {e}")
        return 0
