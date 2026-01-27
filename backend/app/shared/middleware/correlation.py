"""
Request Middleware

Provides middleware for:
1. Correlation ID - Assigns a unique ID to each request for log tracing
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.shared.core.logging import set_correlation_id, get_correlation_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique correlation ID to each request.
    
    Features:
    - Generates a unique ID for each request (req-xxxxxxxx)
    - Accepts an incoming X-Request-ID header if provided (for distributed tracing)
    - Adds X-Request-ID to the response headers
    - Makes the ID available to all loggers via context variable
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Check if client provided a request ID (for distributed tracing)
        incoming_id = request.headers.get("X-Request-ID")
        
        # Set the correlation ID (uses incoming or generates new)
        correlation_id = set_correlation_id(incoming_id)
        
        # Process the request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Request-ID"] = correlation_id
        
        return response
