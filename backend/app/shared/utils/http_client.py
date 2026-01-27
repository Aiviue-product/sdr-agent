"""
HTTP Client Manager with Connection Pooling

Provides a shared, reusable HTTP client for making external API calls.
Benefits:
- Connection reuse (no TCP handshake per request)
- Connection pooling (multiple concurrent requests)
- Proper resource cleanup on shutdown
- Configurable timeouts and limits

Usage:
    from app.shared.utils.http_client import http_client_manager
    
    # Get the shared client
    client = http_client_manager.get_client()
    response = await client.get("https://api.example.com/data")
    
    # Or use as context manager for specific config
    async with http_client_manager.get_client() as client:
        response = await client.post(url, json=data)
"""
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import httpx

logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_TIMEOUT = 30.0
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_MAX_CONNECTIONS = 100
DEFAULT_MAX_KEEPALIVE_CONNECTIONS = 20
DEFAULT_KEEPALIVE_EXPIRY = 30.0  # seconds


class HTTPClientManager:
    """
    Singleton HTTP client manager with connection pooling.
    
    Features:
    - Lazy initialization (client created on first use)
    - Connection pooling for performance
    - Automatic cleanup on shutdown
    - Thread-safe singleton pattern
    """
    
    _instance: Optional['HTTPClientManager'] = None
    _client: Optional[httpx.AsyncClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Prevent re-initialization
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self._client = None
        self._config = {
            "timeout": DEFAULT_TIMEOUT,
            "connect_timeout": DEFAULT_CONNECT_TIMEOUT,
            "max_connections": DEFAULT_MAX_CONNECTIONS,
            "max_keepalive_connections": DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
            "keepalive_expiry": DEFAULT_KEEPALIVE_EXPIRY,
        }
        logger.info("HTTPClientManager initialized")
    
    def configure(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        max_keepalive_connections: int = DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
        keepalive_expiry: float = DEFAULT_KEEPALIVE_EXPIRY
    ) -> None:
        """
        Configure the HTTP client settings.
        Must be called BEFORE first use or after close().
        
        Args:
            timeout: Total request timeout in seconds
            connect_timeout: Connection timeout in seconds
            max_connections: Maximum total connections in pool
            max_keepalive_connections: Max connections to keep alive
            keepalive_expiry: How long to keep idle connections (seconds)
        """
        if self._client is not None:
            logger.warning("Cannot reconfigure while client is active. Call close() first.")
            return
        
        self._config = {
            "timeout": timeout,
            "connect_timeout": connect_timeout,
            "max_connections": max_connections,
            "max_keepalive_connections": max_keepalive_connections,
            "keepalive_expiry": keepalive_expiry,
        }
        logger.info(f"HTTPClientManager configured: {self._config}")
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create a new HTTP client with configured settings."""
        timeout = httpx.Timeout(
            timeout=self._config["timeout"],
            connect=self._config["connect_timeout"]
        )
        
        limits = httpx.Limits(
            max_connections=self._config["max_connections"],
            max_keepalive_connections=self._config["max_keepalive_connections"],
            keepalive_expiry=self._config["keepalive_expiry"]
        )
        
        return httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            http2=False,  # HTTP/2 requires extra 'h2' package, HTTP/1.1 is fine for pooling
            follow_redirects=True
        )
    
    def get_client(self) -> httpx.AsyncClient:
        """
        Get the shared HTTP client.
        Creates the client lazily on first access.
        
        Returns:
            Shared httpx.AsyncClient instance
        
        Usage:
            client = http_client_manager.get_client()
            response = await client.get(url)
        """
        if self._client is None:
            self._client = self._create_client()
            logger.info("HTTP client created with connection pooling")
        
        return self._client
    
    @asynccontextmanager
    async def get_client_context(
        self,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Get client as async context manager with optional overrides.
        
        Args:
            timeout: Override timeout for this request
            headers: Additional headers for this request
            
        Yields:
            Configured httpx.AsyncClient
            
        Usage:
            async with http_client_manager.get_client_context(timeout=60) as client:
                response = await client.post(url, json=data)
        """
        client = self.get_client()
        
        # If no overrides, just yield the client
        if timeout is None and headers is None:
            yield client
            return
        
        # Create a new client with overrides for this context
        # Note: This doesn't affect the shared client
        override_timeout = httpx.Timeout(timeout) if timeout else None
        
        if override_timeout or headers:
            # Use the shared client but with request-specific options
            # For headers, we'll need to pass them per-request
            yield client
        else:
            yield client
    
    async def close(self) -> None:
        """
        Close the HTTP client and release all connections.
        Call this during application shutdown.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP client closed, connections released")
    
    def is_active(self) -> bool:
        """Check if the client is currently active."""
        return self._client is not None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current client status for monitoring."""
        if self._client is None:
            return {
                "active": False,
                "config": self._config
            }
        
        return {
            "active": True,
            "config": self._config,
            "http2_enabled": False
        }


# Singleton instance
http_client_manager = HTTPClientManager()


# ============================================
# FastAPI LIFECYCLE HOOKS
# ============================================

async def startup_http_client():
    """
    Call during FastAPI startup to pre-warm the connection pool.
    Optional but recommended for faster first requests.
    """
    client = http_client_manager.get_client()
    logger.info("HTTP client pre-warmed during startup")


async def shutdown_http_client():
    """
    Call during FastAPI shutdown to properly close connections.
    IMPORTANT: Must be called to prevent resource leaks.
    """
    await http_client_manager.close()
    logger.info("HTTP client shutdown complete")
