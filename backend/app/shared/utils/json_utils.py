"""
JSON Utility Functions
Common utilities for safe JSON parsing and handling.
"""
import json
from typing import Any, Union, List, Dict


def safe_json_parse(
    data: Any, 
    default: Any = None
) -> Union[Dict, List, Any]:
    """
    Safely parse JSON data, handling strings and already-parsed objects.
    
    This utility eliminates the repeated pattern of:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = default
    
    Args:
        data: Input data - can be a JSON string, dict, list, or None
        default: Value to return if parsing fails (default: None)
        
    Returns:
        Parsed data if successful, otherwise the default value
        
    Examples:
        >>> safe_json_parse('{"key": "value"}')
        {'key': 'value'}
        
        >>> safe_json_parse('["a", "b"]')
        ['a', 'b']
        
        >>> safe_json_parse({'already': 'parsed'})
        {'already': 'parsed'}
        
        >>> safe_json_parse('invalid json', default=[])
        []
        
        >>> safe_json_parse(None, default={})
        {}
    """
    # If it's None or empty, return default
    if data is None:
        return default if default is not None else None
    
    # If it's already a dict or list, return as-is
    if isinstance(data, (dict, list)):
        return data
    
    # If it's a string, try to parse it
    if isinstance(data, str):
        if not data.strip():
            return default if default is not None else None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return default if default is not None else None
    
    # For any other type, return default
    return default if default is not None else data


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """
    Safely serialize data to JSON string.
    
    Args:
        data: Data to serialize
        default: Value to return if serialization fails
        
    Returns:
        JSON string
    """
    if data is None:
        return default
    
    if isinstance(data, str):
        return data  # Already a string
    
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return default
