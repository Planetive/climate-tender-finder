# CRITICAL: Set event loop policy BEFORE any other imports that might use asyncio
import sys
import os
import asyncio

# Fix Windows event loop and encoding for Crawl4AI/Playwright
if sys.platform == 'win32':
    # Set UTF-8 encoding for Windows console
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Use ProactorEventLoop for Windows (required for subprocess support - Playwright needs this)
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Load root .env early so SUPABASE_* are available to the store
from services.env_loader import load_env_file
load_env_file()

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import uvicorn
from services.cache_service import clear_cache
from services.opportunity_store import (
    list_opportunities,
    get_opportunity_by_id,
    count_by_source,
)
from services.adb_enrichment import is_stale_posted
from services.content_filter import matches_esg_theme, matches_target_geography
from services.ingest_service import (
    daily_ingest_loop,
    run_full_ingest,
    get_last_ingest_info,
    seconds_until_next_7am_pkt,
)
from services.source_settings import (
    load_settings,
    set_source_enabled,
    source_category,
)
from services.source_health import get_source_health
from config.feeds import config


def _adb_max_posted_age() -> dict:
    """source_id → max posted age days for ADB opportunity feeds."""
    return {
        f["id"]: int(f.get("max_posted_age_days") or 365)
        for f in config["feeds"]
        if (f.get("id") or "").startswith("adb-")
        and f.get("content_kind") == "opportunity"
    }


def _news_source_ids() -> set:
    return {
        f["id"]
        for f in config["feeds"]
        if f.get("content_kind") == "news"
    }


def _filter_target_geo(items: list) -> list:
    """Keep only Pakistan / MENA items (no India, Türkiye, etc.)."""
    return [i for i in items if matches_target_geography(i)]


def _filter_esg_theme(items: list) -> list:
    """
    Opportunities must match ESG-advisory themes (energy, climate finance/risk, industrials).
    News from allowlisted PK sources can pass without theme (business news retention).
    """
    news_ids = _news_source_ids()
    kept = []
    for item in items:
        source = item.get("source") or {}
        sid = (source.get("id") or "") if isinstance(source, dict) else ""
        kind = item.get("content_kind") or ""
        if kind == "news" or sid in news_ids:
            kept.append(item)
            continue
        if matches_esg_theme(item):
            kept.append(item)
    return kept


def _filter_stale_adb(items: list) -> list:
    """
    Hide ADB notices that are past deadline or posted too long ago with no open deadline.
    Safety net so the UI stays clean even before the next DB purge/ingest.
    """
    max_ages = _adb_max_posted_age()
    if not max_ages:
        return items
    kept = []
    for item in items:
        source = item.get("source") or {}
        sid = source.get("id") if isinstance(source, dict) else ""
        if sid in max_ages and is_stale_posted(item, max_age_days=max_ages[sid]):
            continue
        kept.append(item)
    return kept


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the 07:00 Pakistan-time daily ingest loop with the API server."""
    task = asyncio.create_task(daily_ingest_loop())
    wait_s = seconds_until_next_7am_pkt()
    print(f"📅 Scheduler armed — next 07:00 PKT ingest in ~{int(wait_s // 60)} minutes")
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="News Tracker API",
    description="API for climate funding opportunities from RSS feeds and web scraping",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: set CORS_ORIGINS=https://your-app.vercel.app,http://localhost:8080
# Note: browsers forbid Access-Control-Allow-Origin: * when credentials are on.
# So if origins is "*", we disable credentials (fine for this public API).
_cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] or ["*"]
_cors_credentials = "*" not in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "RSS Feed API is running"
    }


@app.get("/api/feeds")
async def get_feeds(
    limit: int = Query(200, ge=1, le=2000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    refresh: bool = Query(False, description="Deprecated: use POST /api/feeds/refresh instead"),
):
    """Serve stored items from Supabase (no scrape on normal page loads).

    Browsing the UI only reads the DB. Scraping runs at 07:00 PKT daily
    or when POST /api/feeds/refresh is called (sidebar button).
    """
    try:
        if refresh:
            # Back-compat: old clients passing refresh=true trigger a full ingest
            await run_full_ingest(trigger="get_refresh_param")

        fetch_limit = min(max(limit + offset, limit), 2000)
        db_items, db_total = await list_opportunities(limit=fetch_limit, offset=0)
        filtered = _filter_target_geo(db_items) if db_items else []
        filtered = _filter_esg_theme(filtered)
        filtered = _filter_stale_adb(filtered)
        page = filtered[offset:offset + limit]
        return {
            "success": True,
            "total": len(filtered),
            "count": len(page),
            "offset": offset,
            "limit": limit,
            "data": page,
            "cached": True,
            "source": "database",
            "last_ingest": get_last_ingest_info(),
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Failed to fetch RSS feeds",
                "message": str(error)
            }
        )


@app.post("/api/feeds/refresh")
async def refresh_feeds():
    """Manual re-run: scrape all sources, upsert, purge news older than 3 days."""
    result = await run_full_ingest(trigger="manual")
    if result.get("running"):
        raise HTTPException(status_code=409, detail=result)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result)
    return result


@app.get("/api/feeds/ingest-status")
async def ingest_status():
    """Last ingest info + seconds until next 07:00 PKT run."""
    from services.ingest_service import missed_todays_scheduled_run

    last = get_last_ingest_info()
    return {
        "success": True,
        "last_ingest": last,
        "seconds_until_next_7am_pkt": int(seconds_until_next_7am_pkt()),
        "missed_todays_7am_pkt": missed_todays_scheduled_run(),
        "timezone": "Asia/Karachi",
        "hint": "For host cron (more reliable than in-process): curl -X POST http://localhost:3001/api/feeds/refresh",
    }


@app.get("/api/feeds/item/{item_id}")
async def get_feed_item(item_id: str):
    """Get a single opportunity by id from Supabase (cheap detail lookup)."""
    try:
        item = await get_opportunity_by_id(item_id)
        if not item:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "Opportunity not found",
                    "message": f"No stored opportunity with id={item_id}",
                },
            )
        return {
            "success": True,
            "data": item,
            "source": "database",
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Failed to fetch opportunity",
                "message": str(error),
            },
        )


@app.get("/api/feeds/source/{source_id}")
async def get_feeds_by_source(source_id: str):
    """Return stored items for one source from Supabase (no live scrape)."""
    try:
        source = next((f for f in config["feeds"] if f["id"] == source_id), None)

        if not source:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "Source not found"
                }
            )

        # Read from DB only — Sources page must stay fast
        db_items, _total = await list_opportunities(limit=2000, offset=0)
        feeds = [
            i for i in _filter_stale_adb(db_items)
            if (i.get("source") or {}).get("id") == source_id
        ]

        return {
            "success": True,
            "source": source["name"],
            "count": len(feeds),
            "data": feeds,
            "source_store": "database",
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Failed to fetch RSS feeds from source",
                "message": str(error)
            }
        )


@app.get("/api/sources")
async def get_sources():
    """List configured sources with enabled flag, category, and DB item counts."""
    settings = load_settings()
    counts = await count_by_source()
    last = get_last_ingest_info() or {}

    sources = []
    for feed in config["feeds"]:
        sid = feed["id"]
        enabled = settings.get(sid, True)
        health = get_source_health(sid)
        health_status = health.get("status")  # ok | empty | error
        if not enabled:
            ui_status = "paused"
        elif health_status == "error":
            ui_status = "error"
        else:
            ui_status = "active"
        sources.append({
            "id": sid,
            "name": feed["name"],
            "type": feed.get("type", "rss"),
            "url": feed["url"],
            "description": feed.get("description", ""),
            "content_kind": feed.get("content_kind", "opportunity"),
            "category": source_category(feed),
            "enabled": enabled,
            "status": ui_status,
            "opportunities_found": counts.get(sid, 0),
            "last_sync": health.get("last_run_at") or last.get("finished_at"),
            "health": {
                "status": health_status,
                "items_kept": health.get("items_kept"),
                "items_raw": health.get("items_raw"),
                "last_error": health.get("last_error"),
                "message": health.get("message"),
                "last_success_at": health.get("last_success_at"),
            },
        })

    return {
        "success": True,
        "count": len(sources),
        "data": sources,
        "last_ingest": last,
    }


@app.post("/api/sources/{source_id}/toggle")
async def toggle_source(source_id: str, enabled: Optional[bool] = Query(None)):
    """
    Turn a source on/off for daily 07:00 PKT and Re-run feeds.
    If enabled is omitted, flips the current value.
    """
    try:
        settings = load_settings()
        if source_id not in settings:
            raise HTTPException(status_code=404, detail={"error": "Source not found"})
        new_value = (not settings[source_id]) if enabled is None else bool(enabled)
        set_source_enabled(source_id, new_value)
        return {
            "success": True,
            "id": source_id,
            "enabled": new_value,
            "status": "active" if new_value else "paused",
        }
    except HTTPException:
        raise
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "Source not found"})
    except Exception as error:
        raise HTTPException(status_code=500, detail={"error": str(error)})


@app.post("/api/cache/clear")
async def clear_cache_endpoint():
    """Clear the cache (force fresh data on next request)"""
    await clear_cache()
    return {
        "success": True,
        "message": "Cache cleared successfully"
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3001"))
    print(f"🚀 Starting News Tracker API server...")
    rss_count = len([f for f in config['feeds'] if f.get('type', 'rss') == 'rss'])
    scrape_count = len([f for f in config['feeds'] if f.get('type') == 'scrape'])
    print(f"📡 Monitoring {rss_count} RSS feed sources and {scrape_count} scraping sources")
    print(f"🌐 CORS origins: {_cors_origins}")
    print(f"⏳ Initializing server on 0.0.0.0:{port}...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        loop="asyncio"
    )
