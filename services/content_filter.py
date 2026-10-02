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
    
    # Combine all searchable text
    search_text = ' '.join([
        item.get('title', ''),
        item.get('description', ''),
        item.get('content', ''),
        ' '.join(item.get('categories', []))
    ]).lower()
    
    # Check if any keyword matches
    has_relevant_keyword = any(
        keyword.lower() in search_text
        for keyword in all_keywords
    )
    
    return has_relevant_keyword


def score_relevance(item: Dict[str, Any], additional_keywords: List[str] = None) -> int:
    """
    Scores content relevance (higher = more relevant)
    
    Args:
        item: Feed item dictionary
        additional_keywords: Additional keywords to search for
        
    Returns:
        Relevance score (number of keyword matches)
    """
    if additional_keywords is None:
        additional_keywords = []
    
    all_keywords = DEFAULT_KEYWORDS + [k.lower() for k in additional_keywords]
    
    search_text = ' '.join([
        item.get('title', ''),
        item.get('description', ''),
        item.get('content', ''),
        ' '.join(item.get('categories', []))
    ]).lower()
    
    score = sum(
        search_text.count(keyword.lower())
        for keyword in all_keywords
    )
    
    return score
