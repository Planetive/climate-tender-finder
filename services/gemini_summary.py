"""
Gemini article summaries with rate-limit pacing.

Ported from the weekly business-news example script:
- sliding-window RPM limiter (stay under free-tier caps)
- short delay between calls
- retry on per-minute limits; fail fast on daily quota

Used for all news sources. Ingest runs priority sources first
(ProPakistani, Arab News, Khaleej), then the rest — same limiter
so later sources wait their turn and do not overrun RPM.
"""
import asyncio
import os
import time
from typing import Any, Dict, List, Optional

# Confirmed from Google AI Studio Rate Limit dashboard (free tier style caps).
# Stay under RPM with a safety margin; wait only as long as needed.
GEMINI_SAFE_RPM = int(os.getenv("GEMINI_SAFE_RPM", "13"))
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "2"))
GEMINI_RETRY_WAIT_SECONDS = int(os.getenv("GEMINI_RETRY_WAIT_SECONDS", "30"))
GEMINI_DELAY = float(os.getenv("GEMINI_DELAY", "1.0"))
# Example script used gemini-3.5-flash-lite; env override + safe fallbacks
GEMINI_SUMMARY_MODEL = os.getenv("GEMINI_SUMMARY_MODEL", "gemini-3.5-flash-lite")
GEMINI_SUMMARY_FALLBACKS = [
    GEMINI_SUMMARY_MODEL,
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
]

_gemini_call_timestamps: List[float] = []
_client = None


def _api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or "").strip()


def _get_client():
    global _client
    if _client is not None:
        return _client
    key = _api_key()
    if not key:
        return None
    try:
        from google import genai

        _client = genai.Client(api_key=key)
        return _client
    except Exception as e:
        print(f"⚠ Could not init Gemini client: {e}")
        return None


def wait_for_rate_limit_slot() -> None:
    """
    Sliding-window limiter: blocks only long enough to guarantee fewer
    than GEMINI_SAFE_RPM calls in the trailing 60 seconds.
    """
    now = time.monotonic()

    while _gemini_call_timestamps and now - _gemini_call_timestamps[0] > 60:
        _gemini_call_timestamps.pop(0)

    if len(_gemini_call_timestamps) >= GEMINI_SAFE_RPM:
        oldest = _gemini_call_timestamps[0]
        wait_seconds = 60 - (now - oldest) + 0.5
        if wait_seconds > 0:
            print(
                f"      Pacing: waiting {wait_seconds:.1f}s "
                f"to stay under {GEMINI_SAFE_RPM} RPM..."
            )
            time.sleep(wait_seconds)
        now = time.monotonic()
        while _gemini_call_timestamps and now - _gemini_call_timestamps[0] > 60:
            _gemini_call_timestamps.pop(0)

    _gemini_call_timestamps.append(time.monotonic())


def is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "429" in text
        or "resource_exhausted" in text
        or "rate limit" in text
        or "quota" in text
    )


def is_daily_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "day" in text or "daily" in text


def summarize_with_gemini(title: str, article_text: str, source: str) -> str:
    """
    ~150-word news summary. Same structure as the example script
    (length, no invented facts, paced calls).
    """
    client = _get_client()
    if not client:
        return "Summary unavailable (GEMINI_API_KEY not set)."

    prompt = f"""
You are a professional news editor covering business, climate, energy,
and sustainable development.

Summarize this {source} news article in approximately 150 words.

Requirements:
- Target 120-160 words.
- Use 2-3 short paragraphs.
- Clearly explain the main development.
- Include important numbers, companies, people, dates, markets or
  financial information when relevant.
- Explain why the development matters.
- Only use information present in the supplied article.
- Do not invent facts.
- Do not give opinions.
- Do not say "this article".
- Do not mention AI.

TITLE:
{title}

ARTICLE:
{(article_text or "")[:12000]}
"""

    models = []
    for m in GEMINI_SUMMARY_FALLBACKS:
        if m and m not in models:
            models.append(m)

    last_error = None
    for model in models:
        for attempt in range(1, GEMINI_MAX_RETRIES + 1):
            wait_for_rate_limit_slot()
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                text = getattr(response, "text", None)
                if text and text.strip():
                    return text.strip()
                last_error = "empty response"
            except Exception as e:
                last_error = e
                if is_daily_quota_error(e):
                    return f"Summary error (daily quota exhausted): {type(e).__name__}: {e}"
                if is_rate_limit_error(e) and attempt < GEMINI_MAX_RETRIES:
                    print(
                        f"      Rate limited on {model} "
                        f"(attempt {attempt}/{GEMINI_MAX_RETRIES}), "
                        f"waiting {GEMINI_RETRY_WAIT_SECONDS}s..."
                    )
                    time.sleep(GEMINI_RETRY_WAIT_SECONDS)
                    continue
                # try next model
                print(f"      Gemini model {model} failed: {e}")
                break

    if last_error:
        return f"Summary error: {type(last_error).__name__}: {last_error}"
    return "Summary unavailable."


def attach_gemini_summaries(items: List[Dict[str, Any]], source_name: str) -> List[Dict[str, Any]]:
    """
    Add ai_summary to each item (and prefer it as description for the UI).
    Sleeps GEMINI_DELAY between articles — same pacing idea as the example.
    Skips items that already have a usable ai_summary (avoids double work).
    """
    if not items:
        return items
    if not _api_key():
        print("⚠ Skipping Gemini summaries — GEMINI_API_KEY not set")
        return items

    pending = [
        item
        for item in items
        if not _has_usable_summary(item.get("ai_summary"))
    ]
    if not pending:
        print(f"  Gemini: {source_name} already summarized — skip")
        return items

    total = len(pending)
    print(f"  Gemini summaries for {source_name}: {total} article(s)...")
    for i, item in enumerate(pending, start=1):
        title = item.get("title") or ""
        body = item.get("content") or item.get("description") or ""
        print(f"    Summarizing {i}/{total}: {title[:70]}")
        summary = summarize_with_gemini(title, body, source_name)
        item["ai_summary"] = summary
        # Priority field for list/detail — UI prefers ai_summary
        if _has_usable_summary(summary):
            item["description"] = summary
        time.sleep(GEMINI_DELAY)
    return items


def _has_usable_summary(summary: Optional[str]) -> bool:
    if not summary or not str(summary).strip():
        return False
    text = str(summary).strip().lower()
    if text.startswith("summary error"):
        return False
    if "unavailable" in text:
        return False
    return True


async def attach_gemini_summaries_async(
    items: List[Dict[str, Any]], source_name: str
) -> List[Dict[str, Any]]:
    """Run attach_gemini_summaries off the event loop (blocking I/O + sleeps)."""
    if not items:
        return items
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: attach_gemini_summaries(items, source_name)
    )
