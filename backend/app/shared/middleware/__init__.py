"""
Shared Middleware
"""
from app.shared.middleware.correlation import CorrelationIdMiddleware

__all__ = ["CorrelationIdMiddleware"]
