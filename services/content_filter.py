from typing import List, Dict, Any

# Default keywords for climate, sustainability, and energy content
DEFAULT_KEYWORDS = [
    # Climate & Environment
    'climate', 'climate change', 'global warming', 'carbon', 'emissions', 'greenhouse',
    'environment', 'environmental', 'sustainability', 'sustainable', 'green',

    # Energy
    'energy', 'renewable', 'solar', 'wind', 'hydroelectric', 'clean energy',
    'fossil fuel', 'electricity', 'power', 'energy efficiency',

    # Funding & Opportunities
    'funding', 'grant', 'tender', 'rfp', 'request for proposal', 'opportunity',
    'partnership', 'call for', 'application', 'bid', 'procurement',

    # Regions
    'pakistan', 'pakistani', 'mena', 'middle east', 'north africa',
    'arab', 'gulf', 'saudi', 'uae', 'egypt', 'jordan', 'lebanon',

    # Related terms
    'conservation', 'biodiversity', 'ecosystem', 'renewable energy',
    'climate action', 'net zero', 'decarbonization', 'mitigation', 'adaptation'
]

# Target geographies: Pakistan, MENA, or clearly Global programs
PAKISTAN_MARKERS = [
    'pakistan', 'pakistani', 'islamabad', 'karachi', 'lahore', 'punjab', 'sindh',
]

MENA_MARKERS = [
    'mena', 'middle east', 'north africa', 'arab', 'gulf',
    'saudi', 'saudi arabia', 'uae', 'united arab emirates', 'dubai', 'abu dhabi',
    'egypt', 'jordan', 'lebanon', 'morocco', 'tunisia', 'algeria',
    'qatar', 'bahrain', 'kuwait', 'oman', 'iraq', 'yemen',
]

GLOBAL_MARKERS = [
    'global', 'worldwide', 'world-wide', 'international', 'multi-country',
    'multicountry', 'cross-border', 'all countries',
]

# Sources that are already scoped to Pakistan or a global climate fund
PAKISTAN_SOURCE_IDS = {
    'paktender',
    'propakistani-business',
    'undp-pakistan-procurement',
    'secp-notifications',
}
GLOBAL_CLIMATE_SOURCE_IDS = {
    'gcf-negotiations',
}


def _search_blob(item: Dict[str, Any]) -> str:
    parts = [
        item.get('title', '') or '',
        item.get('description', '') or '',
        item.get('content', '') or '',
        item.get('country', '') or '',
        item.get('location', '') or '',
        item.get('beneficiary_country', '') or '',
        ' '.join(item.get('categories', []) or []),
    ]
    return ' '.join(parts).lower()


def filter_relevant_content(item: Dict[str, Any], additional_keywords: List[str] = None) -> bool:
    """
    Filters content to check if it's relevant to climate/sustainability/energy

    Args:
        item: Feed item dictionary with title, description, content, categories
        additional_keywords: Additional keywords to search for

    Returns:
        True if item is relevant, False otherwise
    """
    if additional_keywords is None:
        additional_keywords = []

    all_keywords = DEFAULT_KEYWORDS + [k.lower() for k in additional_keywords]
    search_text = _search_blob(item)

    return any(keyword.lower() in search_text for keyword in all_keywords)


def matches_target_geography(item: Dict[str, Any]) -> bool:
    """
    Keep only Pakistan, MENA, or clearly Global opportunities.

    Why: scrapers/RSS often return every country; Planetive focuses on
    Pakistan, MENA, and global climate/funding programs (not every national tender).
    """
    source = item.get('source') or {}
    source_id = ''
    if isinstance(source, dict):
        source_id = (source.get('id') or '').lower()

    if source_id in PAKISTAN_SOURCE_IDS or source_id in GLOBAL_CLIMATE_SOURCE_IDS:
        return True

    text = _search_blob(item)

    if any(m in text for m in PAKISTAN_MARKERS):
        return True
    if any(m in text for m in MENA_MARKERS):
        return True
    if any(m in text for m in GLOBAL_MARKERS):
        return True

    # Structured country/location fields sometimes short
    for field in ('country', 'location', 'beneficiary_country'):
        value = (item.get(field) or '').strip().lower()
        if not value:
            continue
        if value in ('global', 'worldwide', 'international', 'regional'):
            return True
        if any(m in value for m in PAKISTAN_MARKERS + MENA_MARKERS):
            return True

    return False


def passes_content_filters(
    item: Dict[str, Any],
    additional_keywords: List[str] = None,
    skip_keyword_filter: bool = False,
) -> bool:
    """
    Combined gate: optional keyword relevance + always geography (PK / MENA / Global).
    """
    if not matches_target_geography(item):
        return False
    if skip_keyword_filter:
        return True
    return filter_relevant_content(item, additional_keywords)


def score_relevance(item: Dict[str, Any], additional_keywords: List[str] = None) -> int:
    """
    Scores content relevance (higher = more relevant)
    """
    if additional_keywords is None:
        additional_keywords = []

    all_keywords = DEFAULT_KEYWORDS + [k.lower() for k in additional_keywords]
    search_text = _search_blob(item)

    return sum(search_text.count(keyword.lower()) for keyword in all_keywords)
