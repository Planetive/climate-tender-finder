"""
Stamp user-facing labels on items: opportunity_type + relevance.

Why: frontend was guessing "Grant" for almost everything.
Relevance is for an ESG advisory (energy, climate finance/risk, industrials).
"""
from typing import Any, Dict, List

from services.content_filter import (
    ESG_THEME_KEYWORDS,
    MENA_MARKERS,
    PAKISTAN_MARKERS,
    score_relevance,
)


def _blob(item: Dict[str, Any]) -> str:
    parts = [
        item.get("title") or "",
        item.get("description") or "",
        item.get("content") or "",
        item.get("opportunity_type") or "",
        item.get("development_area") or "",
        " ".join(item.get("categories") or []),
    ]
    return " ".join(parts).lower()


def infer_opportunity_type(item: Dict[str, Any], content_kind: str) -> str:
    """Return Grant | RFP | Partnership | Tender | News."""
    if content_kind == "news":
        return "News"

    existing = (item.get("opportunity_type") or "").strip()
    if existing:
        t = existing.lower()
        if "rfp" in t or "rfq" in t or "proposal" in t or "negotiation" in t:
            return "RFP"
        if "tender" in t or "procurement" in t or "bid" in t or "invitation" in t:
            return "Tender"
        if "partner" in t:
            return "Partnership"
        if "grant" in t or "funding" in t:
            return "Grant"
        if "news" in t:
            return "News"

    source = item.get("source") or {}
    sid = (source.get("id") or "").lower() if isinstance(source, dict) else ""
    tender_sources = {
        "paktender",
        "ungm",
        "undp-pakistan-procurement",
        "gcf-negotiations",
        "adb-invitation-for-bids",
        "adb-advanced-notices",
        "adb-csrn",
        "afdb-procurement",
    }
    if sid in tender_sources:
        text = _blob(item)
        if "rfp" in text or "request for proposal" in text:
            return "RFP"
        return "Tender"

    text = _blob(item)
    if "rfp" in text or "request for proposal" in text:
        return "RFP"
    if "tender" in text or "procurement" in text or "bidding" in text:
        return "Tender"
    if "partnership" in text or "partner with" in text:
        return "Partnership"
    if "grant" in text or "funding call" in text or "call for proposals" in text:
        return "Grant"
    return "Grant"


def infer_relevance(item: Dict[str, Any], content_kind: str) -> str:
    """
    High / Medium / Low for ESG-advisory usefulness.

    High: Pakistan/MENA + strong ESG themes (climate finance/risk, energy, ESG, sector)
    Medium: Pakistan/MENA with lighter theme hits, or strong theme without geo stamp
    Low: weak theme match
    """
    text = _blob(item)
    country = (
        item.get("country")
        or item.get("location")
        or item.get("beneficiary_country")
        or ""
    ).lower()

    pk = any(m in text or m in country for m in PAKISTAN_MARKERS)
    mena = any(m in text or m in country for m in MENA_MARKERS)
    in_focus_geo = pk or mena

    high_terms = [
        "esg",
        "climate finance",
        "climate risk",
        "carbon market",
        "mrv",
        "net zero",
        "net-zero",
        "decarbon",
        "sustainable finance",
        "green finance",
        "energy transition",
        "renewable",
        "oil",
        "gas",
        "petroleum",
        "chemical",
        "steel",
        "cement",
        "plastic",
        "paper",
    ]
    medium_terms = [
        "climate",
        "energy",
        "sustainability",
        "carbon",
        "emission",
        "solar",
        "wind",
        "adaptation",
        "mitigation",
    ]

    strong = any(t in text for t in high_terms)
    medium = any(t in text for t in medium_terms)
    score = score_relevance(item)

    if content_kind == "opportunity" and in_focus_geo and strong:
        return "High"
    if in_focus_geo and (strong or score >= 3):
        return "High" if content_kind == "opportunity" else "Medium"
    if in_focus_geo and medium:
        return "Medium"
    if strong or score >= 2:
        return "Medium"
    if medium or any(k in text for k in ESG_THEME_KEYWORDS[:20]):
        return "Low"
    return "Low"


def stamp_labels(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach opportunity_type + relevance onto each item (and keep content_kind)."""
    for item in items:
        kind = item.get("content_kind") or "opportunity"
        item["content_kind"] = kind
        item["opportunity_type"] = infer_opportunity_type(item, kind)
        item["relevance"] = infer_relevance(item, kind)
    return items
