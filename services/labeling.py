"""
Stamp user-facing labels on items: opportunity_type + relevance.

Relevance is for an ESG advisory (energy, climate finance/risk, industrials).
Geography alone (Lebanon / Pakistan) is NOT enough for High — theme must match.
"""
from typing import Any, Dict, List

from services.content_filter import (
    MENA_MARKERS,
    PAKISTAN_MARKERS,
    is_noise_procurement,
    matches_esg_theme,
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


def _whole_word(term: str, text: str) -> bool:
    import re

    if " " in term or "-" in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def infer_opportunity_type(item: Dict[str, Any], content_kind: str) -> str:
    """Return Grant | RFP | Partnership | Tender | Accelerator | Funding | News."""
    if content_kind == "news":
        return "News"

    existing = (item.get("opportunity_type") or "").strip()
    if existing:
        t = existing.lower()
        if "accelerat" in t or "incubator" in t:
            return "Accelerator"
        if "rfp" in t or "rfq" in t or "proposal" in t or "negotiation" in t or "eoi" in t:
            return "RFP"
        if "tender" in t or "procurement" in t or "bid" in t or "invitation" in t:
            return "Tender"
        if "partner" in t:
            return "Partnership"
        if "funding" in t and "grant" not in t:
            return "Funding"
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
        "isdb-procurement",
        "opec-fund-procurement",
        "undp-procurement-pk-uae",
    }
    grant_sources = {
        "akrsp-grants",
    }
    accelerator_sources = {
        "hub71-climatetech",
        "catalyst-uae",
        "accelerate-prosperity-csi",
        "clip-pakistan",
        "digital-pakistan-climate-tech",
        "nic-karachi-ignite",
    }
    funding_sources = {
        "cfa-pakistan",
    }
    existing_type = (item.get("opportunity_type") or "").strip().lower()
    if sid in funding_sources or existing_type == "funding":
        return "Funding"
    if sid in accelerator_sources or existing_type == "accelerator":
        return "Accelerator"
    if sid in grant_sources:
        return "Grant"
    if sid in tender_sources:
        text = _blob(item)
        if (
            "rfp" in text
            or "request for proposal" in text
            or "rfq" in text
            or "expression of interest" in text
            or "eoi" in text
        ):
            return "RFP"
        return "Tender"

    text = _blob(item)
    if "accelerat" in text or "incubator" in text:
        return "Accelerator"
    if "rfp" in text or "request for proposal" in text or "expression of interest" in text:
        return "RFP"
    if "tender" in text or "procurement" in text or "bidding" in text:
        return "Tender"
    if "partnership" in text or "partner with" in text:
        return "Partnership"
    if "startup funding" in text or "seed fund" in text or "venture" in text:
        return "Funding"
    if "grant" in text or "funding call" in text or "call for proposals" in text:
        return "Grant"
    return "Grant"


def infer_relevance(item: Dict[str, Any], content_kind: str) -> str:
    """
    High / Medium / Low for ESG-advisory usefulness.

    High: PK/MENA + clear ESG/energy/climate/sector theme (not office supplies)
    Medium: lighter theme match in focus geo
    Low: noise procurement, or no real theme
    """
    # Photocopiers, elevators, crafts, etc. are never High/Medium
    if is_noise_procurement(item):
        return "Low"

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

    # Strong = phrases an ESG advisor actually cares about (whole words for short ones)
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
        "petroleum",
        "petrochemical",
        "hydrocarbon",
        "oil and gas",
        "oil & gas",
        "chemical",
        "steel",
        "cement",
        "plastic",
        "greenhouse",
        "tcfd",
        "issb",
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
        "renewable",
        "environment",
    ]

    strong = any(_whole_word(t, text) if " " not in t and len(t) <= 8 else t in text for t in high_terms)
    # oil / gas only as whole words (avoid random substring hits)
    if _whole_word("oil", text) or _whole_word("gas", text):
        strong = True

    medium = any(
        _whole_word(t, text) if len(t) <= 8 else t in text for t in medium_terms
    )
    theme_ok = matches_esg_theme(item)
    score = score_relevance(item)

    # Must have a real ESG theme — geography alone is never High
    if not theme_ok:
        return "Low"

    if content_kind == "opportunity" and in_focus_geo and strong:
        return "High"
    if in_focus_geo and strong:
        return "High" if content_kind == "opportunity" else "Medium"
    if in_focus_geo and medium and score >= 2:
        return "High" if content_kind == "opportunity" else "Medium"
    if in_focus_geo and (medium or score >= 1):
        return "Medium"
    if strong:
        return "Medium"
    return "Low"


def stamp_labels(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach opportunity_type + relevance onto each item (and keep content_kind)."""
    for item in items:
        kind = item.get("content_kind") or "opportunity"
        item["content_kind"] = kind
        item["opportunity_type"] = infer_opportunity_type(item, kind)
        item["relevance"] = infer_relevance(item, kind)
    return items
