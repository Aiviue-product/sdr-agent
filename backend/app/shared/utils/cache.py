"""
Simple In-Memory Cache with TTL and LRU Eviction

Features:
- TTL (Time To Live) for automatic expiration
- Max size with LRU (Least Recently Used) eviction
- Pattern-based invalidation
- Async-safe operations
- Fail-safe (returns None on errors, never crashes)

IMPORTANT: This is a single-instance cache. If you scale to multiple
server instances, you'll need Redis or similar distributed cache.
"""
import asyncio
import logging
import time
import fnmatch
from typing import Any, Optional, Dict
from collections import OrderedDict
from dataclasses import dataclass

logger = logging.getLogger("cache")


@dataclass
class CacheEntry:
    """A single cache entry with data and expiration time."""
    data: Any
    expires_at: float  # Unix timestamp


class SimpleCache:
    """
    Thread-safe in-memory cache with TTL and LRU eviction.
    
    Usage:
        cache = SimpleCache(max_size=100)
        
        # Set with TTL
        cache.set("keywords", ["hiring", "recruiting"], ttl_seconds=120)
        
        # Get (returns None if expired or missing)
        result = cache.get("keywords")
        
        # Invalidate
        cache.invalidate("keywords")
        cache.invalidate_pattern("rate_limits:*")
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of entries before LRU eviction kicks in
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Returns:
            Cached data if exists and not expired, None otherwise
        """
        try:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            # Check if expired
            if time.time() > entry.expires_at:
                # Remove expired entry
                self._cache.pop(key, None)
                self._stats["misses"] += 1
                logger.debug(f"Cache EXPIRED: {key}")
                return None
            
            # Move to end for LRU tracking
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            logger.debug(f"Cache HIT: {key}")
            return entry.data
            
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None
    
    def set(self, key: str, data: Any, ttl_seconds: int = 60) -> bool:
        """
        Set a value in cache with TTL.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl_seconds: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Evict if at max size
            while len(self._cache) >= self._max_size:
                # Remove oldest (first) item
                oldest_key = next(iter(self._cache))
                self._cache.pop(oldest_key)
                logger.debug(f"Cache LRU eviction: {oldest_key}")
            
            expires_at = time.time() + ttl_seconds
            self._cache[key] = CacheEntry(data=data, expires_at=expires_at)
            self._cache.move_to_end(key)
            
            logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
            return True
            
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False
    
    def invalidate(self, key: str) -> bool:
        """
        Remove a specific key from cache.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if key existed, False otherwise
        """
        try:
            if key in self._cache:
                self._cache.pop(key)
                self._stats["invalidations"] += 1
                logger.info(f"Cache INVALIDATED: {key}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Cache invalidate error for {key}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Remove all keys matching a pattern (supports * and ? wildcards).
        
        Args:
            pattern: Glob pattern like "rate_limits:*" or "user:*:profile"
            
        Returns:
            Number of keys invalidated
        """
        try:
            # Find matching keys (iterate over a copy to avoid modification during iteration)
            keys_to_remove = [
                key for key in list(self._cache.keys())
                if fnmatch.fnmatch(key, pattern)
            ]
            
            for key in keys_to_remove:
                self._cache.pop(key, None)
            
            if keys_to_remove:
                self._stats["invalidations"] += len(keys_to_remove)
                logger.info(f"Cache INVALIDATED pattern '{pattern}': {len(keys_to_remove)} keys")
            
            return len(keys_to_remove)
            
        except Exception as e:
            logger.warning(f"Cache invalidate_pattern error for {pattern}: {e}")
            return 0
    
    def clear_all(self) -> int:
        """
        Clear all entries from cache.
        
        Returns:
            Number of entries cleared
        """
        try:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache CLEARED: {count} entries")
            return count
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            **self._stats,
            "size": len(self._cache),
            "max_size": self._max_size,
            "hit_rate": self._stats["hits"] / max(1, self._stats["hits"] + self._stats["misses"])
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries. Call periodically if needed.
        
        Returns:
            Number of expired entries removed
        """
        try:
            now = time.time()
            expired_keys = [
                key for key, entry in list(self._cache.items())
                if now > entry.expires_at
            ]
            
            for key in expired_keys:
                self._cache.pop(key, None)
            
            if expired_keys:
                logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
            
            return len(expired_keys)
            
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")
            return 0


# ============================================
# GLOBAL CACHE INSTANCE
# ============================================

# Single cache instance for the application
# For multi-instance deployments, replace with Redis
app_cache = SimpleCache(max_size=100)


# ============================================
# CACHE KEY CONSTANTS
# ============================================

# Define cache keys as constants to avoid typos
CACHE_KEY_KEYWORDS = "linkedin:keywords"
CACHE_KEY_RATE_LIMITS = "linkedin:rate_limits"  # Will append date

# TTL values in seconds
CACHE_TTL_KEYWORDS = 120  # 2 minutes
CACHE_TTL_RATE_LIMITS = 30  # 30 seconds (needs to be fresh)


def get_rate_limits_cache_key() -> str:
    """Get the rate limits cache key for today."""
    from datetime import date
    return f"{CACHE_KEY_RATE_LIMITS}:{date.today().isoformat()}"
