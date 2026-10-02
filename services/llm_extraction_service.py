"""
LLM-based extraction service for opportunities using OpenRouter
Extracts structured data, classifies opportunity types, and scores actionability
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Use a free model - Google Gemini Flash is recommended
DEFAULT_MODEL = "google/gemini-flash-1.5"  # Free tier model

# Fallback free models if primary fails
FALLBACK_MODELS = [
    "meta-llama/llama-3.2-3b-instruct:free",  # Free tier
    "mistralai/mistral-7b-instruct:free",     # Free tier
]


def create_extraction_prompt(item: Dict[str, Any]) -> str:
    """
    Create a prompt for LLM to extract structured opportunity data
    """
    title = item.get('title', '')
    description = item.get('description', '')
    content = item.get('content', '')[:2000]  # Limit content length
    
    prompt = f"""Analyze the following opportunity and extract structured information.

Title: {title}
Description: {description}
Content: {content[:2000]}

Extract the following information in JSON format:
{{
    "opportunity_type": "RFP|Grant|Tender|Partnership|Program|EOI|Other",
    "deadline": "YYYY-MM-DD or null if not found",
    "amount": "dollar amount or range or null",
    "eligibility": "brief eligibility criteria or null",
    "contact_email": "contact email if found or null",
    "contact_phone": "contact phone if found or null",
    "is_active": true/false (true if deadline is in future or not specified),
    "is_climate_related": true/false,
    "actionability_score": 0-100 (higher = more actionable for climate/sustainability projects),
    "relevance_summary": "brief 1-2 sentence summary of why this is relevant"
}}

Rules:
- Only extract information that is explicitly stated in the text
- If information is not found, use null
- actionability_score should be high (80+) if: has deadline, has amount, is climate-related, is active
- actionability_score should be low (<50) if: expired, not climate-related, vague requirements
- Return ONLY valid JSON, no additional text
"""
    return prompt


async def extract_with_llm(item: Dict[str, Any], model: str = None) -> Optional[Dict[str, Any]]:
    """
    Extract structured opportunity data using OpenRouter LLM
    
    Args:
        item: Dictionary with title, description, content
        model: Model to use (defaults to DEFAULT_MODEL)
        
    Returns:
        Extracted structured data or None if extraction fails
    """
    if not OPENROUTER_API_KEY:
        print("⚠ OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
        return None
    
    model = model or DEFAULT_MODEL
    prompt = create_extraction_prompt(item)
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo",  # Optional: for OpenRouter analytics
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert at analyzing funding opportunities, grants, RFPs, and tenders. Extract structured data accurately."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,  # Low temperature for consistent extraction
        "max_tokens": 500,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Parse JSON from response
            # Sometimes LLM wraps JSON in markdown code blocks
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            extracted_data = json.loads(content)
            
            # Merge extracted data with original item
            enhanced_item = {**item, **extracted_data}
            
            return enhanced_item
            
    except json.JSONDecodeError as e:
        print(f"⚠ Failed to parse LLM response as JSON: {str(e)}")
        # Try fallback model if available
        if model != FALLBACK_MODELS[0] and FALLBACK_MODELS:
            print(f"  Trying fallback model: {FALLBACK_MODELS[0]}")
            return await extract_with_llm(item, model=FALLBACK_MODELS[0])
        return None
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:  # Rate limit
            print(f"⚠ OpenRouter rate limit reached. Please wait or upgrade your plan.")
        else:
            print(f"⚠ OpenRouter API error: {e.response.status_code} - {e.response.text}")
        return None
        
    except Exception as e:
        print(f"⚠ LLM extraction error: {str(e)}")
        return None


def is_actionable_opportunity(item: Dict[str, Any]) -> bool:
    """
    Determine if an opportunity is actionable based on extracted data
    
    Args:
        item: Item with extracted LLM data
        
    Returns:
        True if opportunity is actionable
    """
    # Check if LLM extraction was successful
    if 'actionability_score' not in item:
        return False
    
    score = item.get('actionability_score', 0)
    is_active = item.get('is_active', False)
    is_climate_related = item.get('is_climate_related', False)
    opportunity_type = item.get('opportunity_type', '').lower()
    
    # Must be climate-related
    if not is_climate_related:
        return False
    
    # Must be active
    if not is_active:
        return False
    
    # Must be a valid opportunity type
    valid_types = ['rfp', 'grant', 'tender', 'partnership', 'program', 'eoi']
    if opportunity_type not in valid_types and opportunity_type != 'other':
        return False
    
    # Actionability score threshold (adjust as needed)
    if score < 60:
        return False
    
    return True


async def enhance_opportunity_with_llm(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance an opportunity item with LLM-extracted structured data
    
    Args:
        item: Basic opportunity item from RSS/scraping
        
    Returns:
        Enhanced item with extracted data, or original item if extraction fails
    """
    # Only enhance if it passes basic keyword filtering
    # (to avoid wasting API calls on irrelevant content)
    
    # Try LLM extraction
    enhanced = await extract_with_llm(item)
    
    if enhanced:
        # Add extraction metadata
        enhanced['llm_extracted'] = True
        enhanced['llm_extraction_date'] = datetime.now().isoformat()
        enhanced['is_actionable'] = is_actionable_opportunity(enhanced)
        return enhanced
    else:
        # Return original item if extraction fails
        item['llm_extracted'] = False
        item['is_actionable'] = False
        return item
