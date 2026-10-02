"""
AI-based content filtering service using Google Gemini API
Filters content to ensure it's only related to specific climate/sustainability topics
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
import httpx

# Google Gemini API configuration
# Fallback: set GEMINI_API_KEY in the environment (do not hardcode secrets)
_DEFAULT_GEMINI_KEY = ""
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or _DEFAULT_GEMINI_KEY
# Use v1 stable API endpoint
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"

# Available Gemini models (from ListModels)
# We only use models that support generateContent
GEMINI_MODELS = [
    "gemini-2.5-flash",        # Primary
    "gemini-2.0-flash",        # Fallback
    "gemini-2.0-flash-lite",   # Fallback (cheaper / lighter)
]

DEFAULT_MODEL = GEMINI_MODELS[0]  # Use Gemini 2.5 Flash by default

# Free-tier pacing: wait between calls so we don't hit rate limits
RATE_LIMIT_DELAY_SECONDS = int(os.getenv("AI_FILTER_DELAY_SECONDS", "40"))
DEFAULT_BATCH_SIZE = 1  # Sequential by default on free tier

# Topics that content must be related to
REQUIRED_TOPICS = [
    "climate change",
    "sustainability",
    "sustainable development",
    "decarbonization",
    "carbon emissions",
    "climate resilience",
    "environmental impact",
    "green transition",
    "renewable energy",
    "solar power",
    "wind energy",
    "clean energy",
    "energy transition",
    "power generation",
    "ESG",
    "sustainable finance",
    "green finance",
    "climate finance",
    "impact investing",
    "carbon credits",
]


def create_relevance_prompt(item: Dict[str, Any]) -> str:
    """
    Create a prompt for LLM to determine if content is relevant to required topics
    """
    title = item.get('title', '')
    description = item.get('description', '')
    content = item.get('content', '')[:3000]  # Limit content length for API efficiency
    
    topics_list = ", ".join(REQUIRED_TOPICS)
    
    prompt = f"""You are a content classifier. Determine if the following article/content is relevant to ANY of these specific topics:

{topics_list}

Article Title: {title}
Article Description: {description}
Article Content: {content[:3000]}

Your task:
1. Analyze if this content is related to ANY of the topics listed above
2. Content must be DIRECTLY related to at least one topic (not just tangentially mentioned)
3. Return your response as JSON with this exact format:
{{
    "is_relevant": true/false,
    "relevant_topics": ["list", "of", "matching", "topics"],
    "confidence": 0-100,
    "reason": "brief explanation of why it is or isn't relevant"
}}

Rules:
- Only return true if content is DIRECTLY related to at least one of the required topics
- If content only mentions a topic in passing or as a minor reference, return false
- If content is about general news, politics, or unrelated topics, return false
- Be strict: only climate/sustainability/energy/finance content should pass
- Return ONLY valid JSON, no additional text or markdown formatting
"""
    return prompt


async def check_relevance_with_ai(
    item: Dict[str, Any], 
    model: str = None,
    max_retries: int = 2
) -> Optional[Dict[str, Any]]:
    """
    Use Google Gemini API to check if content is relevant to required topics
    
    Args:
        item: Dictionary with title, description, content
        model: Model to use (defaults to DEFAULT_MODEL)
        max_retries: Maximum number of retries with different models
        
    Returns:
        Dictionary with relevance check results, or None if check fails
        Format: {
            "is_relevant": bool,
            "relevant_topics": List[str],
            "confidence": int,
            "reason": str,
            "model_used": str
        }
    """
    if not GEMINI_API_KEY:
        print("⚠ Google Gemini API key not found. AI filtering disabled. Set GEMINI_API_KEY environment variable.")
        return None
    
    model = model or DEFAULT_MODEL
    prompt = create_relevance_prompt(item)
    
    # Gemini API endpoint
    url = GEMINI_API_URL.format(model=model)
    
    headers = {
        "Content-Type": "application/json",
    }
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.1,  # Low temperature for consistent classification
            "maxOutputTokens": 300,
        }
    }
    
    # Try with primary model, then fallback models if needed
    models_to_try = [model] + [m for m in GEMINI_MODELS if m != model]
    
    for attempt, current_model in enumerate(models_to_try[:max_retries + 1]):
        try:
            current_url = GEMINI_API_URL.format(model=current_model)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Gemini API uses API key as query parameter
                response = await client.post(
                    current_url,
                    headers=headers,
                    json=payload,
                    params={"key": GEMINI_API_KEY}
                )
                
                # Debug: Print response status and first 200 chars if error
                if response.status_code != 200:
                    print(f"⚠ Gemini API returned status {response.status_code}")
                    print(f"   URL: {current_url}")
                    print(f"   Response: {response.text[:300]}")
                
                response.raise_for_status()
                
                result = response.json()
                
                # Extract content from Gemini response
                # Gemini response structure: candidates[0].content.parts[0].text
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0].get('content', {}).get('parts', [{}])[0].get('text', '')
                else:
                    print(f"⚠ Unexpected Gemini response structure: {result}")
                    continue
                
                # Parse JSON from response
                # Sometimes LLM wraps JSON in markdown code blocks
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                
                relevance_data = json.loads(content)
                
                # Validate response structure
                if 'is_relevant' not in relevance_data:
                    raise ValueError("Missing 'is_relevant' field in LLM response")
                
                # Add metadata
                relevance_data['model_used'] = current_model
                relevance_data['ai_filtered'] = True
                
                return relevance_data
                
        except json.JSONDecodeError as e:
            if attempt < max_retries:
                print(f"⚠ Failed to parse Gemini response as JSON (attempt {attempt + 1}): {str(e)}")
                print(f"   Response content: {content[:200] if 'content' in locals() else 'N/A'}")
                continue
            else:
                print(f"⚠ Failed to parse Gemini response after {max_retries + 1} attempts: {str(e)}")
                return None
                
        except httpx.HTTPStatusError as e:
            # Get full error details
            try:
                error_json = e.response.json()
                error_message = error_json.get('error', {}).get('message', 'Unknown error')
                error_code = error_json.get('error', {}).get('code', e.response.status_code)
            except:
                error_message = e.response.text[:500] if e.response.text else "No error details"
                error_code = e.response.status_code
            
            # Show actual error instead of assuming rate limit
            if e.response.status_code == 429:  # Rate limit — wait and retry same model once
                print(f"⚠ Google Gemini rate limit reached: {error_message}")
                print(f"   Waiting {RATE_LIMIT_DELAY_SECONDS}s before retry...")
                await asyncio.sleep(RATE_LIMIT_DELAY_SECONDS)
                if attempt < max_retries:
                    continue
                return None
            elif e.response.status_code == 400:  # Bad request - likely API format issue
                print(f"⚠ Gemini API bad request (check API format): {error_message}")
                print(f"   Model used: {current_model}")
                print(f"   URL: {current_url}")
                if attempt < max_retries:
                    continue  # Try next model
                return None
            elif e.response.status_code == 404:  # Model not found
                print(f"⚠ Gemini model not found: {current_model}")
                print(f"   Error: {error_message}")
                if attempt < max_retries:
                    continue  # Try next model
                return None
            elif e.response.status_code >= 500:  # Server error - try next model
                if attempt < max_retries:
                    print(f"⚠ Gemini server error (attempt {attempt + 1}): {e.response.status_code} - {error_message}")
                    continue
                else:
                    print(f"⚠ Gemini API error: {e.response.status_code} - {error_message}")
                    return None
            else:
                print(f"⚠ Gemini API error ({e.response.status_code}): {error_message}")
                return None
                
        except Exception as e:
            if attempt < max_retries:
                print(f"⚠ Gemini filtering error (attempt {attempt + 1}): {str(e)}")
                continue
            else:
                print(f"⚠ Gemini filtering error after {max_retries + 1} attempts: {str(e)}")
                return None
    
    return None


async def filter_content_with_ai(
    items: List[Dict[str, Any]],
    model: str = None,
    batch_size: int = None
) -> List[Dict[str, Any]]:
    """
    Filter a list of content items using AI to keep only relevant ones.
    
    Free-tier safe: processes one item at a time by default and waits
    RATE_LIMIT_DELAY_SECONDS (40s) between calls so we stay under limits.
    
    Args:
        items: List of content items to filter
        model: Model to use for filtering
        batch_size: Concurrent items per batch (default 1 for free tier)
        
    Returns:
        List of items that passed AI relevance check
    """
    if not GEMINI_API_KEY:
        print("⚠ AI filtering disabled: GEMINI_API_KEY not set")
        return items  # Return all items if AI filtering is not available
    
    if batch_size is None:
        batch_size = DEFAULT_BATCH_SIZE
    
    relevant_items = []
    total = len(items)
    
    print(f"🤖 AI filtering {total} items (batch_size={batch_size}, delay={RATE_LIMIT_DELAY_SECONDS}s between batches)")
    
    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"   Batch {batch_num}/{total_batches}: checking {len(batch)} item(s)...")
        
        # Process batch (usually size 1 on free tier)
        tasks = [check_relevance_with_ai(item, model) for item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter items based on AI results
        for item, result in zip(batch, results):
            if isinstance(result, Exception):
                print(f"⚠ Error checking relevance for item '{item.get('title', 'Unknown')}': {result}")
                # On error, skip the item (strict filtering)
                continue
            
            if result and result.get('is_relevant', False):
                # Add AI filtering metadata to item
                item['ai_filtered'] = True
                item['ai_relevance'] = result
                relevant_items.append(item)
            else:
                # Item filtered out
                if result:
                    print(f"❌ Filtered out: '{item.get('title', 'Unknown')[:50]}...' - {result.get('reason', 'Not relevant')}")
                else:
                    print(f"❌ Filtered out: '{item.get('title', 'Unknown')[:50]}...' - AI check failed")
        
        # Pause between batches to stay under free-tier rate limits
        if i + batch_size < total:
            print(f"   ⏳ Waiting {RATE_LIMIT_DELAY_SECONDS}s before next batch (free-tier pacing)...")
            await asyncio.sleep(RATE_LIMIT_DELAY_SECONDS)
    
    print(f"✅ AI filtering complete: {len(relevant_items)}/{total} items passed relevance check")
    return relevant_items


def is_relevant_sync(item: Dict[str, Any]) -> bool:
    """
    Synchronous check if item has already been AI-filtered and is relevant
    Use this to check items that have already been processed
    
    Args:
        item: Item that may have AI filtering metadata
        
    Returns:
        True if item is relevant (based on existing AI check), False otherwise
    """
    if not item.get('ai_filtered', False):
        return False  # Not AI filtered yet
    
    ai_relevance = item.get('ai_relevance', {})
    return ai_relevance.get('is_relevant', False)
