"""
Logging Configuration with Correlation ID Support

This module provides:
1. A context variable to store the current request's correlation ID
2. A custom log formatter that includes the correlation ID
3. A helper function to get the current correlation ID
"""
import logging
import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable to store the correlation ID for the current request
# This is thread-safe and works with async code
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    """Get the current request's correlation ID."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set the correlation ID for the current request.
    If not provided, generates a new UUID.
    
    Returns the correlation ID that was set.
    """
    if correlation_id is None:
        correlation_id = f"req-{uuid.uuid4().hex[:8]}"
    correlation_id_var.set(correlation_id)
    return correlation_id


class CorrelationIdFilter(logging.Filter):
    """
    A logging filter that adds the correlation_id to log records.
    This allows the formatter to include the correlation ID in log messages.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "no-request"
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure the logging system with correlation ID support.
    
    This sets up a custom formatter that includes:
    - Timestamp
    - Correlation ID (request ID)
    - Logger name
    - Log level
    - Message
    """
    # Create a custom format that includes correlation ID
    log_format = "%(asctime)s | [%(correlation_id)s] | %(name)s | %(levelname)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # Create handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicate logs
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)
    
    root_logger.addHandler(handler)
    
    # Also configure uvicorn access logs to use our format
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.addHandler(handler)
