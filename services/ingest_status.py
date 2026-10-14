"""
Persist last ingest run + optional webhook for ops health.

Why: without this, a failed 7AM job is invisible.
File: config/ingest_status.json
Env: INGEST_WEBHOOK_URL — optional POST JSON on each finished run
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

_PATH = Path(__file__).resolve().parent.parent / "config" / "ingest_status.json"


def load_ingest_status() -> Optional[Dict[str, Any]]:
    if not _PATH.is_file():
        return None
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as e:
        print(f"⚠ Could not read ingest_status.json: {e}")
        return None


def save_ingest_status(result: Dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")


async def notify_ingest_webhook(result: Dict[str, Any]) -> None:
    """Fire-and-forget style notify (awaited, but failures only log)."""
    url = (os.getenv("INGEST_WEBHOOK_URL") or "").strip()
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=result)
            if response.status_code >= 400:
                print(f"⚠ Ingest webhook HTTP {response.status_code}: {response.text[:200]}")
            else:
                print("✓ Ingest webhook notified")
    except Exception as e:
        print(f"⚠ Ingest webhook error: {e}")
