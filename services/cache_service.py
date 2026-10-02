"""
Simple in-memory cache service for RSS feeds and scraped content
This prevents refetching data on every API request, significantly improving performance
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio

# In-memory cache storage
_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = asyncio.Lock()

# Default cache TTL (Time To Live) - 10 minutes
DEFAULT_CACHE_TTL_MINUTES = 10


def get_cache_key(source_configs: List[Dict[str, Any]]) -> str:
    """
    Generate a cache key from source configurations
    Uses source IDs to create a unique key
    """
    source_ids = sorted([s.get('id', '') for s in source_configs])
    return f"feeds:{':'.join(source_ids)}"


async def get_cached_data(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached data if it exists and hasn't expired
    
    Returns:
        Cached data if available and fresh, None otherwise
    """
    async with _cache_lock:
        if cache_key not in _cache:
            return None
        
        cache_entry = _cache[cache_key]
        expires_at = cache_entry.get('expires_at')
        
        # Check if cache has expired
        if expires_at and datetime.now() > expires_at:
            # Remove expired cache
            del _cache[cache_key]
            return None
        
        # Return cached data
        return cache_entry.get('data')


async def set_cached_data(cache_key: str, data: List[Dict[str, Any]], ttl_minutes: int = DEFAULT_CACHE_TTL_MINUTES):
    """
    Store data in cache with expiration time
    
    Args:
        cache_key: Unique key for this cache entry
        data: Data to cache
        ttl_minutes: Time to live in minutes (how long to keep the cache)
    """
    async with _cache_lock:
        expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
        _cache[cache_key] = {
            'data': data,
            'expires_at': expires_at,
            'cached_at': datetime.now()
        }


async def clear_cache():
    """
    Clear all cached data
    Useful for manual refresh or when sources change
    """
    async with _cache_lock:
        _cache.clear()


async def get_cache_info() -> Dict[str, Any]:
    """
    Get information about the cache (for debugging/monitoring)
    """
    async with _cache_lock:
        cache_info = {}
        for key, entry in _cache.items():
            cache_info[key] = {
                'cached_at': entry.get('cached_at').isoformat() if entry.get('cached_at') else None,
                'expires_at': entry.get('expires_at').isoformat() if entry.get('expires_at') else None,
                'item_count': len(entry.get('data', []))
            }
        return cache_info
