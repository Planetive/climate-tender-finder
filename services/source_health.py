"""
Per-source health: last success / error / item counts.

Why: dead RSS feeds used to fail silently; the Sources page looked fine.
Persisted to config/source_health.json so it survives API restarts.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_PATH = Path(__file__).resolve().parent.parent / "config" / "source_health.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_health() -> Dict[str, Any]:
    if not _PATH.is_file():
        return {"sources": {}}
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"sources": {}}
        data.setdefault("sources", {})
        return data
    except Exception as e:
        print(f"⚠ Could not read source_health.json: {e}")
        return {"sources": {}}


def save_health(data: Dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_source_ok(
    source_id: str,
    items_kept: int,
    items_raw: Optional[int] = None,
    message: str = "",
) -> None:
    data = load_health()
    sources = data.setdefault("sources", {})
    sources[source_id] = {
        "status": "ok" if items_kept > 0 else "empty",
        "last_success_at": _now_iso(),
        "last_run_at": _now_iso(),
        "items_kept": items_kept,
        "items_raw": items_raw if items_raw is not None else items_kept,
        "last_error": None,
        "message": message or ("ok" if items_kept > 0 else "Fetched but 0 items after filters"),
    }
    save_health(data)


def record_source_error(source_id: str, error: str) -> None:
    data = load_health()
    sources = data.setdefault("sources", {})
    prev = sources.get(source_id) or {}
    sources[source_id] = {
        **prev,
        "status": "error",
        "last_run_at": _now_iso(),
        "last_error": (error or "Unknown error")[:500],
        "message": "Fetch failed",
    }
    save_health(data)


def get_source_health(source_id: str) -> Dict[str, Any]:
    return (load_health().get("sources") or {}).get(source_id) or {}
