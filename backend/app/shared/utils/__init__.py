"""
Shared Utility Functions
"""
from app.shared.utils.json_utils import safe_json_parse, safe_json_dumps
from app.shared.utils.cache import (
    app_cache,
    CACHE_KEY_KEYWORDS,
    CACHE_KEY_RATE_LIMITS,
    CACHE_TTL_KEYWORDS,
    CACHE_TTL_RATE_LIMITS,
    get_rate_limits_cache_key
)
from app.shared.utils.exceptions import ConcurrentModificationError, EntityNotFoundError
from app.shared.utils.phone_utils import (
    validate_phone,
    normalize_phone_number,
    is_valid_phone,
    is_mobile_number,
    get_phone_info,
    PhoneValidationResult
)

__all__ = [
    "safe_json_parse", 
    "safe_json_dumps",
    "app_cache",
    "CACHE_KEY_KEYWORDS",
    "CACHE_KEY_RATE_LIMITS",
    "CACHE_TTL_KEYWORDS",
    "CACHE_TTL_RATE_LIMITS",
    "get_rate_limits_cache_key",
    "ConcurrentModificationError",
    "EntityNotFoundError",
    # Phone utilities
    "validate_phone",
    "normalize_phone_number",
    "is_valid_phone",
    "is_mobile_number",
    "get_phone_info",
    "PhoneValidationResult"
]
