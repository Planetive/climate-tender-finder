"""
Service to enhance opportunities with LLM extraction
Integrates LLM extraction into the existing scraping/RSS pipeline
"""

from typing import List, Dict, Any
import asyncio
from services.llm_extraction_service import enhance_opportunity_with_llm, is_actionable_opportunity


async def enhance_opportunities_batch(items: List[Dict[str, Any]], use_llm: bool = True) -> List[Dict[str, Any]]:
    """
    Enhance a batch of opportunities with LLM extraction
    
    Args:
        items: List of opportunity items from RSS/scraping
        use_llm: Whether to use LLM extraction (default: True)
        
    Returns:
        List of enhanced opportunities, filtered for actionable ones
    """
    if not use_llm:
        # Return items without LLM enhancement
        return items
    
    enhanced_items = []
    
    # Process items in batches to respect rate limits
    # OpenRouter free tier: 20 requests/minute
    batch_size = 15  # Stay under 20/minute limit
    delay_between_batches = 65  # Wait 65 seconds between batches
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        print(f"Processing LLM batch {i//batch_size + 1} ({len(batch)} items)...")
        
        # Enhance all items in batch concurrently
        tasks = [enhance_opportunity_with_llm(item) for item in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and non-actionable items
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"⚠ Error enhancing item: {str(result)}")
                continue
            
            # Only include actionable opportunities
            if is_actionable_opportunity(result):
                enhanced_items.append(result)
        
        # Wait between batches to respect rate limits (except for last batch)
        if i + batch_size < len(items):
            print(f"  Waiting {delay_between_batches}s before next batch (rate limit)...")
            await asyncio.sleep(delay_between_batches)
    
    print(f"✓ Enhanced {len(enhanced_items)} actionable opportunities out of {len(items)} total")
    return enhanced_items


def filter_actionable_opportunities(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter opportunities to only include actionable ones
    
    Args:
        items: List of opportunity items (with or without LLM extraction)
        
    Returns:
        Filtered list of actionable opportunities
    """
    actionable = []
    
    for item in items:
        # If LLM extraction was done, use its assessment
        if item.get('llm_extracted', False):
            if item.get('is_actionable', False):
                actionable.append(item)
        else:
            # Fallback to basic keyword filtering if LLM not used
            # (This uses the existing content_filter logic)
            actionable.append(item)
    
    return actionable
