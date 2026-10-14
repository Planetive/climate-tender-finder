"""
Daily ingest + news retention + per-source health.

- Runs once per day at 07:00 Asia/Karachi (Pakistan time)
- On API startup: catch-up if today's 07:00 PKT run was missed
- Manual re-run via POST /api/feeds/refresh
- News older than NEWS_RETENTION_DAYS deleted; opportunities kept
"""
import asyncio
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from config.feeds import config as all_config, news_source_ids, stamp_content_kind
from services.cache_service import get_cache_key, set_cached_data
from services.content_filter import matches_target_geography
from services.ingest_status import load_ingest_status, notify_ingest_webhook, save_ingest_status
from services.adb_enrichment import is_stale_posted
from services.labeling import stamp_labels
from services.opportunity_store import (
    delete_old_news,
    delete_stale_adb_opportunities,
    upsert_opportunities,
)
from services.rss_service import fetch_single_feed
from services.scraper_service import scrape_single_url
from services.source_health import record_source_error, record_source_ok
from services.source_settings import get_enabled_feed_configs

PKT = ZoneInfo("Asia/Karachi")
NEWS_RETENTION_DAYS = 3

_ingest_lock = asyncio.Lock()
_last_run: Optional[Dict[str, Any]] = None


def get_last_ingest_info() -> Optional[Dict[str, Any]]:
    """Prefer in-memory; fall back to disk so status survives restarts."""
    if _last_run:
        return _last_run
    return load_ingest_status()


def seconds_until_next_7am_pkt(now: Optional[datetime] = None) -> float:
    """Seconds until the next 07:00 in Pakistan time."""
    now = now or datetime.now(PKT)
    target = datetime.combine(now.date(), time(7, 0), tzinfo=PKT)
    if now >= target:
        target = target + timedelta(days=1)
    return max(1.0, (target - now).total_seconds())


def todays_7am_pkt(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(PKT)
    return datetime.combine(now.date(), time(7, 0), tzinfo=PKT)


def missed_todays_scheduled_run(now: Optional[datetime] = None) -> bool:
    """
    True if it is already past 07:00 PKT today and we have no successful
    scheduled/catch-up/manual run finished after today's 07:00.
    """
    now = now or datetime.now(PKT)
    seven = todays_7am_pkt(now)
    if now < seven:
        return False

    last = get_last_ingest_info() or {}
    if not last.get("success"):
        return True

    finished = last.get("finished_at") or ""
    try:
        # Support +05:00 and Z
        finished_dt = datetime.fromisoformat(finished.replace("Z", "+00:00"))
        if finished_dt.tzinfo is None:
            finished_dt = finished_dt.replace(tzinfo=PKT)
        finished_pkt = finished_dt.astimezone(PKT)
        return finished_pkt < seven
    except Exception:
        return True


async def _fetch_one_source(feed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch a single RSS or scrape source; raises on hard failure."""
    if feed.get("type") == "scrape":
        return await scrape_single_url(feed)
    return await fetch_single_feed(feed)


async def run_full_ingest(trigger: str = "manual") -> Dict[str, Any]:
    """
    Scrape enabled sources one-by-one (records health), label, upsert, purge news.
    """
    global _last_run

    if _ingest_lock.locked():
        return {
            "success": False,
            "message": "Ingest already running — try again when it finishes",
            "running": True,
        }

    async with _ingest_lock:
        started = datetime.now(PKT)
        print(f"\n⏱ Ingest started ({trigger}) at {started.isoformat()}")

        try:
            enabled_feeds = get_enabled_feed_configs()
            skipped = len(all_config["feeds"]) - len(enabled_feeds)
            print(f"  Enabled sources: {len(enabled_feeds)} (skipped {skipped} disabled)")

            if not enabled_feeds:
                finished = datetime.now(PKT)
                _last_run = {
                    "success": True,
                    "trigger": trigger,
                    "started_at": started.isoformat(),
                    "finished_at": finished.isoformat(),
                    "items": 0,
                    "upserted": 0,
                    "news_deleted": 0,
                    "sources_run": 0,
                    "sources_ok": 0,
                    "sources_error": 0,
                    "sources_skipped": skipped,
                    "message": "All sources are disabled — nothing to scrape",
                }
                save_ingest_status(_last_run)
                await notify_ingest_webhook(_last_run)
                print("⚠ No enabled sources — ingest skipped")
                return _last_run

            all_items: List[Dict[str, Any]] = []
            sources_ok = 0
            sources_error = 0
            source_results = []

            for feed in enabled_feeds:
                sid = feed["id"]
                name = feed.get("name", sid)
                try:
                    raw_items = await _fetch_one_source(feed)
                    raw_count = len(raw_items or [])
                    kept = [i for i in (raw_items or []) if matches_target_geography(i)]
                    # Drop past deadlines / decade-old ADB notices with no open deadline
                    max_age = int(feed.get("max_posted_age_days") or 365)
                    kept = [
                        i
                        for i in kept
                        if not is_stale_posted(i, max_age_days=max_age)
                    ]
                    kept = stamp_content_kind(kept, [feed])
                    kept = stamp_labels(kept)
                    all_items.extend(kept)
                    record_source_ok(sid, len(kept), items_raw=raw_count)
                    sources_ok += 1
                    source_results.append(
                        {"id": sid, "name": name, "status": "ok", "items": len(kept)}
                    )
                    print(f"  ✓ {name}: {len(kept)} kept (raw {raw_count})")
                except Exception as e:
                    sources_error += 1
                    record_source_error(sid, str(e))
                    source_results.append(
                        {"id": sid, "name": name, "status": "error", "error": str(e)[:200]}
                    )
                    print(f"  ✗ {name}: {e}")

            cache_key = get_cache_key(enabled_feeds)
            await set_cached_data(cache_key, all_items, ttl_minutes=60 * 12)

            written = await upsert_opportunities(all_items)
            deleted = await delete_old_news(
                news_source_ids=news_source_ids(),
                older_than_days=NEWS_RETENTION_DAYS,
            )
            # Remove ADB rows already in DB that are old/expired (upsert never deletes)
            adb_max_age = {
                f["id"]: int(f.get("max_posted_age_days") or 365)
                for f in all_config["feeds"]
                if (f.get("id") or "").startswith("adb-")
                and f.get("content_kind") == "opportunity"
            }
            stale_deleted = await delete_stale_adb_opportunities(adb_max_age)

            finished = datetime.now(PKT)
            # Overall success if we finished; flag soft failure if everything errored
            overall_ok = sources_error == 0 or sources_ok > 0
            _last_run = {
                "success": overall_ok,
                "trigger": trigger,
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "items": len(all_items),
                "upserted": written,
                "news_deleted": deleted,
                "stale_adb_deleted": stale_deleted,
                "sources_run": len(enabled_feeds),
                "sources_ok": sources_ok,
                "sources_error": sources_error,
                "sources_skipped": skipped,
                "sources": source_results,
            }
            if sources_ok == 0 and sources_error > 0:
                _last_run["success"] = False
                _last_run["error"] = f"All {sources_error} enabled sources failed"
            if written == 0 and sources_ok > 0:
                _last_run["warning"] = "Ingest finished but 0 items were upserted"

            save_ingest_status(_last_run)
            await notify_ingest_webhook(_last_run)
            print(
                f"✓ Ingest done ({trigger}): {len(all_items)} items, "
                f"upserted={written}, errors={sources_error}, "
                f"news_deleted={deleted}, stale_adb_deleted={stale_deleted}"
            )
            return _last_run
        except Exception as e:
            finished = datetime.now(PKT)
            _last_run = {
                "success": False,
                "trigger": trigger,
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "error": str(e),
            }
            save_ingest_status(_last_run)
            await notify_ingest_webhook(_last_run)
            print(f"✗ Ingest failed ({trigger}): {e}")
            return _last_run


async def maybe_catch_up_missed_run() -> None:
    """If past 07:00 PKT and today's run was missed (e.g. server was down), run now."""
    if not missed_todays_scheduled_run():
        print("📅 Catch-up: not needed (already ran after today's 07:00 PKT, or before 07:00)")
        return
    print("📅 Catch-up: missed today's 07:00 PKT run — starting ingest now")
    await run_full_ingest(trigger="startup_catchup")


async def daily_ingest_loop() -> None:
    """Background loop: sleep until 07:00 PKT, then ingest + purge."""
    print("📅 Daily ingest scheduler started (07:00 Asia/Karachi)")
    # Small delay so API is ready, then catch up if overnight restart skipped 7AM
    await asyncio.sleep(5)
    try:
        await maybe_catch_up_missed_run()
    except Exception as e:
        print(f"⚠ Catch-up error: {e}")

    while True:
        wait_s = seconds_until_next_7am_pkt()
        next_at = datetime.now(PKT) + timedelta(seconds=wait_s)
        print(f"  Next scheduled ingest: {next_at.strftime('%Y-%m-%d %H:%M %Z')} (in {int(wait_s)}s)")
        try:
            await asyncio.sleep(wait_s)
            await run_full_ingest(trigger="schedule_7am_pkt")
        except asyncio.CancelledError:
            print("📅 Daily ingest scheduler stopped")
            raise
        except Exception as e:
            print(f"⚠ Scheduler loop error: {e}")
            await asyncio.sleep(60)
