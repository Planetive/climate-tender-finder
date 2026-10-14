"""
Persist which sources are enabled for daily / manual ingest.

Why: the Sources page toggle used to be UI-only (React state).
Settings live in config/source_settings.json so restarts keep your choices.
"""
import json
from pathlib import Path
from typing import Any, Dict

from config.feeds import config

_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "config" / "source_settings.json"


def _default_enabled_map() -> Dict[str, bool]:
    return {f["id"]: bool(f.get("enabled", True)) for f in config["feeds"]}


def load_settings() -> Dict[str, bool]:
    """Return {source_id: enabled}. Missing ids default to True (or feed config)."""
    defaults = _default_enabled_map()
    if not _SETTINGS_PATH.is_file():
        return defaults
    try:
        raw = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        saved = raw.get("enabled") if isinstance(raw, dict) else {}
        if not isinstance(saved, dict):
            return defaults
        merged = dict(defaults)
        for sid, val in saved.items():
            if sid in merged:
                merged[sid] = bool(val)
        return merged
    except Exception as e:
        print(f"⚠ Could not read source_settings.json: {e}")
        return defaults


def save_settings(enabled_map: Dict[str, bool]) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"enabled": enabled_map}
    _SETTINGS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def is_source_enabled(source_id: str) -> bool:
    return bool(load_settings().get(source_id, True))


def set_source_enabled(source_id: str, enabled: bool) -> Dict[str, bool]:
    settings = load_settings()
    if source_id not in settings:
        raise KeyError(f"Unknown source id: {source_id}")
    settings[source_id] = bool(enabled)
    save_settings(settings)
    return settings


def get_enabled_feed_configs() -> list:
    """Feed configs that should run in 7AM / Re-run ingest."""
    settings = load_settings()
    return [f for f in config["feeds"] if settings.get(f["id"], True)]


def source_category(feed: Dict[str, Any]) -> str:
    """User-facing category for the Sources list."""
    kind = feed.get("content_kind") or "opportunity"
    name = (feed.get("name") or "").lower()
    sid = (feed.get("id") or "").lower()

    if kind == "news":
        if "propakistani" in sid:
            return "Pakistan Business News"
        if "unep" in sid or "un " in name:
            return "UN News"
        if "adb" in sid:
            return "ADB News"
        if "worldbank" in sid or "world bank" in name:
            return "World Bank News"
        if "afdb" in sid:
            return "AfDB News"
        return "News & Updates"

    # Opportunities
    if "paktender" in sid or "secp" in sid:
        return "Pakistan Procurement"
    if "undp" in sid:
        return "UN Procurement"
    if "ungm" in sid:
        return "UN Procurement"
    if "gcf" in sid:
        return "Climate Funds"
    if "adb" in sid:
        return "ADB Procurement"
    if "afdb" in sid:
        return "AfDB Procurement"
    return "Funding & Tenders"
