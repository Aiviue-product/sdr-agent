"""
WATI Template Cache
Simple in-memory cache for WATI templates with TTL-based expiration.

Features:
- TTL (Time-To-Live) based automatic expiration
- Manual invalidation for immediate refresh
- Thread-safe for async operations
- Singleton pattern for global access

Cache Invalidation Strategy:
1. Automatic: Templates expire after TTL (default 5 minutes)
2. Manual: Call invalidate_templates() to force refresh on next fetch
3. On-demand: Pass force_refresh=True to get_templates_cached()
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger("wati_cache")

# Default cache TTL (5 minutes)
DEFAULT_TEMPLATE_TTL_SECONDS = 300


@dataclass
class CacheEntry:
    """Single cache entry with data and expiration tracking."""
    data: Any
    created_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = DEFAULT_TEMPLATE_TTL_SECONDS
    
    @property
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time
    
    @property
    def expires_in_seconds(self) -> int:
        """Seconds until expiration (0 if already expired)."""
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        remaining = (expiry_time - datetime.now()).total_seconds()
        return max(0, int(remaining))


class WATICache:
    """
    In-memory cache for WATI data with TTL-based expiration.
    
    Usage:
        cache = WATICache()
        
        # Check cache first
        templates = cache.get_templates()
        if templates is None:
            # Fetch from WATI API
            templates = await wati_client.get_templates()
            cache.set_templates(templates)
        
        # Force refresh
        cache.invalidate_templates()
        
        # Check cache status
        status = cache.get_status()
    """
    
    def __init__(self, ttl_seconds: int = DEFAULT_TEMPLATE_TTL_SECONDS):
        self._templates_cache: Optional[CacheEntry] = None
        self._template_by_name_cache: Dict[str, CacheEntry] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
        
        logger.info(f"WATI Cache initialized with TTL={ttl_seconds}s")
    
    # ============================================
    # TEMPLATES CACHE
    # ============================================
    
    def get_templates(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached templates if available and not expired.
        
        Returns:
            List of templates if cache hit, None if cache miss or expired.
        """
        if self._templates_cache is None:
            logger.debug("Templates cache: MISS (empty)")
            return None
        
        if self._templates_cache.is_expired:
            logger.debug("Templates cache: MISS (expired)")
            self._templates_cache = None
            return None
        
        logger.debug(f"Templates cache: HIT (expires in {self._templates_cache.expires_in_seconds}s)")
        return self._templates_cache.data
    
    def set_templates(self, templates: List[Dict[str, Any]], ttl_seconds: Optional[int] = None) -> None:
        """
        Cache the templates list.
        
        Args:
            templates: List of template dictionaries from WATI
            ttl_seconds: Optional custom TTL (uses default if not provided)
        """
        ttl = ttl_seconds or self._ttl_seconds
        self._templates_cache = CacheEntry(data=templates, ttl_seconds=ttl)
        
        # Also update the by-name cache for quick lookups
        self._template_by_name_cache.clear()
        for template in templates:
            name = template.get("elementName")
            if name:
                self._template_by_name_cache[name] = CacheEntry(
                    data=template, 
                    ttl_seconds=ttl
                )
        
        logger.info(f"Templates cached: {len(templates)} templates, TTL={ttl}s")
    
    def get_template_by_name(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template by name from cache.
        
        Returns:
            Template dict if found and not expired, None otherwise.
        """
        entry = self._template_by_name_cache.get(template_name)
        
        if entry is None:
            logger.debug(f"Template '{template_name}' cache: MISS (not found)")
            return None
        
        if entry.is_expired:
            logger.debug(f"Template '{template_name}' cache: MISS (expired)")
            del self._template_by_name_cache[template_name]
            return None
        
        logger.debug(f"Template '{template_name}' cache: HIT")
        return entry.data
    
    # ============================================
    # INVALIDATION
    # ============================================
    
    def invalidate_templates(self) -> None:
        """
        Invalidate all template caches immediately.
        Call this when you know templates have changed (e.g., admin refresh).
        """
        self._templates_cache = None
        self._template_by_name_cache.clear()
        logger.info("Templates cache invalidated")
    
    def invalidate_all(self) -> None:
        """
        Invalidate all caches.
        Use this for complete cache reset.
        """
        self.invalidate_templates()
        logger.info("All WATI caches invalidated")
    
    # ============================================
    # STATUS & DEBUGGING
    # ============================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current cache status for debugging/monitoring.
        
        Returns:
            Dict with cache statistics and state.
        """
        templates_status = "empty"
        templates_count = 0
        templates_expires_in = 0
        
        if self._templates_cache:
            if self._templates_cache.is_expired:
                templates_status = "expired"
            else:
                templates_status = "valid"
                templates_count = len(self._templates_cache.data) if self._templates_cache.data else 0
                templates_expires_in = self._templates_cache.expires_in_seconds
        
        return {
            "templates": {
                "status": templates_status,
                "count": templates_count,
                "expires_in_seconds": templates_expires_in,
                "by_name_cache_size": len(self._template_by_name_cache)
            },
            "ttl_seconds": self._ttl_seconds
        }
    
    def __repr__(self) -> str:
        status = self.get_status()
        return f"WATICache(templates={status['templates']['status']}, count={status['templates']['count']})"


# ============================================
# SINGLETON INSTANCE
# ============================================

# Global cache instance - import this in other modules
wati_cache = WATICache()


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_cache() -> WATICache:
    """Get the global WATI cache instance."""
    return wati_cache


def invalidate_wati_cache() -> None:
    """Convenience function to invalidate all WATI caches."""
    wati_cache.invalidate_all()
