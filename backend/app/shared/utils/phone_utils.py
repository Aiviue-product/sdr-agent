"""
Phone Number Validation and Normalization Utilities

Uses Google's libphonenumber (via phonenumbers package) for:
- Proper validation of phone numbers
- Normalization to E.164 format
- Country code detection
- Support for international numbers
"""
import re
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat, PhoneNumberType
from phonenumbers import is_valid_number, is_possible_number, format_number, number_type

logger = logging.getLogger(__name__) 


@dataclass
class PhoneValidationResult:
    """Result of phone number validation."""
    is_valid: bool
    normalized: str  # E.164 format without + (e.g., "919876543210")
    e164: str  # Full E.164 format (e.g., "+919876543210")
    country_code: str  # Country code (e.g., "91")
    national_number: str  # National number (e.g., "9876543210")
    country: str  # Country code ISO (e.g., "IN")
    number_type: str  # "mobile", "fixed_line", "unknown", etc.
    error: Optional[str] = None


def validate_phone(
    phone: str,
    default_country: str = "IN"
) -> PhoneValidationResult:
    """
    Validate and parse a phone number using libphonenumber.
    
    Args:
        phone: The phone number to validate (any format)
        default_country: Default country code if not in number (ISO 3166-1 alpha-2)
        
    Returns:
        PhoneValidationResult with validation status and normalized formats
        
    Examples:
        >>> validate_phone("9876543210", "IN")
        PhoneValidationResult(is_valid=True, normalized="919876543210", ...)
        
        >>> validate_phone("+1 (555) 123-4567")
        PhoneValidationResult(is_valid=True, normalized="15551234567", ...)
        
        >>> validate_phone("invalid")
        PhoneValidationResult(is_valid=False, error="Invalid phone number")
    """
    if not phone:
        return PhoneValidationResult(
            is_valid=False,
            normalized="",
            e164="",
            country_code="",
            national_number="",
            country="",
            number_type="unknown",
            error="Phone number is empty"
        )
    
    # Clean the input
    phone = phone.strip()
    
    # Try to parse the number
    try:
        # If number starts with + or 00, parse without default country
        if phone.startswith('+') or phone.startswith('00'):
            parsed = phonenumbers.parse(phone, None)
        else:
            # Try with default country
            parsed = phonenumbers.parse(phone, default_country)
        
        # Check if it's a valid number
        if not is_valid_number(parsed):
            # Check if it's at least a possible number (correct length)
            if not is_possible_number(parsed):
                return PhoneValidationResult(
                    is_valid=False,
                    normalized="",
                    e164="",
                    country_code=str(parsed.country_code) if parsed.country_code else "",
                    national_number=str(parsed.national_number) if parsed.national_number else "",
                    country="",
                    number_type="unknown",
                    error="Phone number has invalid length"
                )
            else:
                return PhoneValidationResult(
                    is_valid=False,
                    normalized="",
                    e164="",
                    country_code=str(parsed.country_code) if parsed.country_code else "",
                    national_number=str(parsed.national_number) if parsed.national_number else "",
                    country="",
                    number_type="unknown",
                    error="Phone number format is invalid for the region"
                )
        
        # Get the country
        country = phonenumbers.region_code_for_number(parsed) or ""
        
        # Get number type
        num_type = number_type(parsed)
        type_map = {
            PhoneNumberType.MOBILE: "mobile",
            PhoneNumberType.FIXED_LINE: "fixed_line",
            PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_line_or_mobile",
            PhoneNumberType.TOLL_FREE: "toll_free",
            PhoneNumberType.PREMIUM_RATE: "premium_rate",
            PhoneNumberType.VOIP: "voip",
            PhoneNumberType.PERSONAL_NUMBER: "personal",
            PhoneNumberType.PAGER: "pager",
            PhoneNumberType.UAN: "uan",
            PhoneNumberType.VOICEMAIL: "voicemail",
            PhoneNumberType.UNKNOWN: "unknown",
        }
        phone_type = type_map.get(num_type, "unknown")
        
        # Format to E.164
        e164 = format_number(parsed, PhoneNumberFormat.E164)  # +919876543210
        normalized = e164.lstrip('+')  # 919876543210
        
        return PhoneValidationResult(
            is_valid=True,
            normalized=normalized,
            e164=e164,
            country_code=str(parsed.country_code),
            national_number=str(parsed.national_number),
            country=country,
            number_type=phone_type
        )
        
    except NumberParseException as e:
        error_messages = {
            NumberParseException.INVALID_COUNTRY_CODE: "Invalid country code",
            NumberParseException.NOT_A_NUMBER: "Not a valid phone number",
            NumberParseException.TOO_SHORT_AFTER_IDD: "Number too short after country code",
            NumberParseException.TOO_SHORT_NSN: "National number too short",
            NumberParseException.TOO_LONG: "Phone number too long",
        }
        error_msg = error_messages.get(e.error_type, f"Invalid phone number: {str(e)}")
        
        return PhoneValidationResult(
            is_valid=False,
            normalized="",
            e164="",
            country_code="",
            national_number="",
            country="",
            number_type="unknown",
            error=error_msg
        )
    except Exception as e:
        logger.error(f"Unexpected error validating phone {phone}: {str(e)}")
        return PhoneValidationResult(
            is_valid=False,
            normalized="",
            e164="",
            country_code="",
            national_number="",
            country="",
            number_type="unknown",
            error=f"Validation error: {str(e)}"
        )


def normalize_phone_number(
    phone: str,
    default_country: str = "IN",
    strict: bool = False
) -> str:
    """
    Normalize a phone number to E.164 format (without +).
    
    This is a convenience function that returns just the normalized string.
    
    Args:
        phone: Phone number in any format
        default_country: Default country if not specified in number
        strict: If True, returns empty string for invalid numbers.
                If False, returns best-effort normalization.
    
    Returns:
        Normalized phone number (e.g., "919876543210") or empty string if invalid
        
    Examples:
        >>> normalize_phone_number("9876543210")
        "919876543210"
        
        >>> normalize_phone_number("+1-555-123-4567")
        "15551234567"
        
        >>> normalize_phone_number("invalid", strict=True)
        ""
        
        >>> normalize_phone_number("9876543210", default_country="US")
        "19876543210"
    """
    result = validate_phone(phone, default_country)
    
    if result.is_valid:
        return result.normalized
    
    if strict:
        return ""
    
    # Best-effort fallback: just extract digits
    # This maintains backward compatibility
    cleaned = re.sub(r'\D', '', phone)
    cleaned = cleaned.lstrip('0')
    
    # If it looks like a 10-digit Indian number, add country code
    if len(cleaned) == 10 and default_country == "IN":
        return "91" + cleaned
    
    return cleaned


def is_valid_phone(phone: str, default_country: str = "IN") -> bool:
    """
    Check if a phone number is valid.
    
    Args:
        phone: Phone number to validate
        default_country: Default country code
        
    Returns:
        True if valid, False otherwise
    """
    return validate_phone(phone, default_country).is_valid


def is_mobile_number(phone: str, default_country: str = "IN") -> bool:
    """
    Check if a phone number is a mobile number.
    
    Args:
        phone: Phone number to check
        default_country: Default country code
        
    Returns:
        True if it's a mobile number, False otherwise
    """
    result = validate_phone(phone, default_country)
    return result.is_valid and result.number_type in ("mobile", "fixed_line_or_mobile")


def get_phone_info(phone: str, default_country: str = "IN") -> dict:
    """
    Get detailed information about a phone number.
    
    Args:
        phone: Phone number to analyze
        default_country: Default country code
        
    Returns:
        Dictionary with phone number details
    """
    result = validate_phone(phone, default_country)
    return {
        "is_valid": result.is_valid,
        "normalized": result.normalized,
        "e164": result.e164,
        "country_code": result.country_code,
        "national_number": result.national_number,
        "country": result.country,
        "number_type": result.number_type,
        "error": result.error
    }
