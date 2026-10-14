"""
Content gates for Planetive ESG advisory focus.

Geography: Pakistan + MENA only (not India, Türkiye, or other countries).
Theme: energy / ESG / climate finance & risk / industrials (oil & gas, chemicals,
paper, plastics, steel, etc.) — what an ESG advisory needs for clients like
Mari, OGDCL, and manufacturing companies.
"""
from typing import Any, Dict, List, Optional

# --- Geography: Pakistan + MENA only -----------------------------------------

PAKISTAN_MARKERS = [
    "pakistan", "pakistani", "islamabad", "karachi", "lahore", "punjab", "sindh",
    "balochistan", "khyber", "peshawar", "rawalpindi",
]

# MENA core — Türkiye is NOT included (user: drop India / Türkiye / similar)
MENA_MARKERS = [
    "mena", "middle east", "north africa", "arab", "gulf", "gcc",
    "saudi", "saudi arabia", "uae", "united arab emirates", "dubai", "abu dhabi",
    "egypt", "jordan", "lebanon", "morocco", "tunisia", "algeria",
    "qatar", "bahrain", "kuwait", "oman", "iraq", "yemen", "palestine",
]

# Explicit out-of-scope (reject even if text also says "energy" / "global")
OUT_OF_SCOPE_MARKERS = [
    "india", "indian", "bangladesh", "sri lanka", "nepal", "bhutan", "maldives",
    "afghanistan", "china", "chinese", "indonesia", "philippines", "vietnam",
    "thailand", "malaysia", "myanmar", "cambodia", "laos", "mongolia",
    "turkey", "türkiye", "turkiye", "turkish", "azerbaijan", "georgia",
    "kenya", "nigeria", "ethiopia", "ghana", "tanzania", "uganda",
    "micronesia", "fiji", "papua", "samoa", "tonga",
    "brazil", "mexico", "colombia", "chile", "peru", "argentina",
]

# Sources already scoped to Pakistan (or a single global climate-finance portal)
PAKISTAN_SOURCE_IDS = {
    "paktender",
    "propakistani-business",
    "undp-pakistan-procurement",
    "secp-notifications",
}
# GCF is climate finance by definition — keep even when country says Global
GLOBAL_CLIMATE_SOURCE_IDS = {
    "gcf-negotiations",
}

# --- Theme: ESG advisory + industrial clients --------------------------------

ESG_THEME_KEYWORDS = [
    # Core advisory themes
    "esg", "environment social governance",
    "climate", "climate change", "climate finance", "climate risk",
    "climate adaptation", "climate mitigation", "climate resilience",
    "carbon", "carbon market", "carbon credit", "ghg", "greenhouse",
    "net zero", "net-zero", "decarbon", "emission", "emissions",
    "sustainability", "sustainable finance", "sustainable",
    "green finance", "green bond", "green sukuk", "transition finance",
    "mrv", "tcfd", "issb", "csrd", "sasb", "gri",
    "adaptation", "mitigation",
    # Energy
    "energy", "renewable", "solar", "wind", "hydro", "power", "electricity",
    "clean energy", "energy efficiency", "energy transition", "grid",
    "fossil", "fuel", "lng", "hydrogen",
    # Finance (climate / ESG context words often nearby — still useful alone for tenders)
    "climate finance", "blended finance", "green loan", "sustainable bond",
    "impact investing", "responsible investment",
    # Industrial / client sectors (Mari, OGDCL, chemicals, paper, plastic, steel, …)
    "oil", "gas", "petroleum", "hydrocarbon", "upstream", "downstream",
    "refinery", "refining", "ogdcl", "exploration",
    "chemical", "petrochemical", "fertilizer", "fertiliser",
    "steel", "iron", "metal", "mining", "mineral",
    "cement", "cement kiln",
    "paper", "pulp", "packaging",
    "plastic", "plastics", "polymer", "polymer",
    "textile", "apparel", "garment",
    "manufacturing", "industrial", "heavy industry",
    "waste", "wastewater", "effluent", "pollution",
    "water treatment", "desalination",
]

# Kept for backward-compatible imports / scoring helpers
DEFAULT_KEYWORDS = list(ESG_THEME_KEYWORDS)


def _search_blob(item: Dict[str, Any]) -> str:
    parts = [
        item.get("title", "") or "",
        item.get("description", "") or "",
        item.get("content", "") or "",
        item.get("country", "") or "",
        item.get("location", "") or "",
        item.get("beneficiary_country", "") or "",
        item.get("development_area", "") or "",
        " ".join(item.get("categories", []) or []),
    ]
    return " ".join(parts).lower()


def _structured_country(item: Dict[str, Any]) -> str:
    return (
        item.get("country")
        or item.get("location")
        or item.get("beneficiary_country")
        or ""
    ).strip().lower()


def _source_id(item: Dict[str, Any]) -> str:
    source = item.get("source") or {}
    if isinstance(source, dict):
        return (source.get("id") or "").lower()
    return ""


def is_out_of_scope_country(item: Dict[str, Any]) -> bool:
    """True when country/text clearly points outside Pakistan + MENA (e.g. India, Türkiye)."""
    country = _structured_country(item)
    text = _search_blob(item)
    hay = f"{country} {text}"

    # If Pakistan or MENA is clearly present, do not treat as out-of-scope
    if any(m in hay for m in PAKISTAN_MARKERS + MENA_MARKERS):
        return False

    if country and any(m in country for m in OUT_OF_SCOPE_MARKERS):
        return True
    if any(m in text for m in OUT_OF_SCOPE_MARKERS):
        return True
    return False


def matches_target_geography(item: Dict[str, Any]) -> bool:
    """
    Keep only Pakistan + MENA (and allowlisted PK / GCF sources).

    Why: we do not scrape grants/tenders for India, Türkiye, or other regions.
    Broad "global/international" wording used to let those through — removed.
    """
    sid = _source_id(item)
    if sid in PAKISTAN_SOURCE_IDS or sid in GLOBAL_CLIMATE_SOURCE_IDS:
        return True

    if is_out_of_scope_country(item):
        return False

    country = _structured_country(item)
    text = _search_blob(item)

    # Structured country is the strongest signal (ADB Countries: field)
    if country:
        if any(m in country for m in PAKISTAN_MARKERS + MENA_MARKERS):
            return True
        # Specific other country set (e.g. "Micronesia…") → drop
        vague = {"", "global", "worldwide", "international", "regional", "not specified", "n/a"}
        if country not in vague:
            return False

    if any(m in text for m in PAKISTAN_MARKERS):
        return True
    if any(m in text for m in MENA_MARKERS):
        return True

    return False


def matches_esg_theme(
    item: Dict[str, Any],
    additional_keywords: Optional[List[str]] = None,
) -> bool:
    """
    True when text matches ESG-advisory themes / industrial client sectors.
    """
    extra = [k.lower() for k in (additional_keywords or []) if k]
    keywords = ESG_THEME_KEYWORDS + extra
    search_text = _search_blob(item)
    return any(keyword.lower() in search_text for keyword in keywords)


def filter_relevant_content(
    item: Dict[str, Any],
    additional_keywords: List[str] = None,
) -> bool:
    """Alias used by scrapers — ESG theme match."""
    return matches_esg_theme(item, additional_keywords)


def passes_content_filters(
    item: Dict[str, Any],
    additional_keywords: List[str] = None,
    skip_keyword_filter: bool = False,
) -> bool:
    """
    Combined gate: geography (PK/MENA) + ESG theme (unless skipped for news).
    """
    if not matches_target_geography(item):
        return False
    if skip_keyword_filter:
        return True
    return matches_esg_theme(item, additional_keywords)


def score_relevance(item: Dict[str, Any], additional_keywords: List[str] = None) -> int:
    """Higher = more ESG-theme keyword hits (simple ranking helper)."""
    extra = [k.lower() for k in (additional_keywords or []) if k]
    keywords = ESG_THEME_KEYWORDS + extra
    search_text = _search_blob(item)
    return sum(search_text.count(keyword.lower()) for keyword in keywords)
