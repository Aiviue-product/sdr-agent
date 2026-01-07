import logging
import httpx
import pandas as pd
from app.core.config import settings
from app.core.constants import (
    ZEROBOUNCE_VALIDATE_URL,
    ZEROBOUNCE_BULK_VALIDATE_URL,
    TIMEOUT_ZEROBOUNCE_INDIVIDUAL,
    TIMEOUT_ZEROBOUNCE_BULK
)

logger = logging.getLogger("email_service") 

async def verify_individual(email: str) -> tuple[str, str]:
    """
    Verifies a single email using async httpx.
    Strict Returns: ('valid', 'Verified') OR ('invalid', 'Review Required')
    """
    if not email or pd.isna(email):
        return "invalid", "Review Required"
    
    # Clean the email string
    email = str(email).strip()
    
    params = {
        "api_key": settings.ZEROBOUNCE_API_KEY, 
        "email": email, 
        "ip_address": "" 
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_ZEROBOUNCE_INDIVIDUAL) as client:
            response = await client.get(ZEROBOUNCE_VALIDATE_URL, params=params)
        
        if response.status_code != 200:
            logger.error(f"API Error for email validation: {response.status_code}")
            # Treat API errors as invalid/review required for safety
            return "invalid", "Review Required"
            
        data = response.json()
        
        if 'status' in data:
            zb_status = data['status'].lower()
            
            # --- STRICT LOGIC ---
            if zb_status == 'valid':
                return 'valid', 'Verified'
            else:
                # Force ANY other status (catch-all, unknown, do_not_mail) to be 'invalid'
                return 'invalid', 'Review Required'
        
        return "invalid", "Review Required"

    except Exception as e:
        logger.error(f"Exception validating email: {str(e)}")
        return "invalid", "Review Required"

async def verify_bulk_batch(email_list: list) -> dict:
    """
    Sends up to 100 emails to ZeroBounce Bulk API using async httpx.
    Returns raw dict: { 'email@domain.com': 'valid' }
    """
    if not email_list: 
        return {}
    
    clean_emails = [str(e).strip() for e in email_list if e and not pd.isna(e)]

    payload = {
        "api_key": settings.ZEROBOUNCE_API_KEY,
        "email_batch": [{"email_address": e, "ip_address": ""} for e in clean_emails]
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_ZEROBOUNCE_BULK) as client:
            response = await client.post(ZEROBOUNCE_BULK_VALIDATE_URL, json=payload)
        
        if response.status_code != 200:
             logger.error(f"Bulk API HTTP Error {response.status_code}")
             return {}

        data = response.json()
        results_map = {}
        
        if 'email_batch' in data:
            for item in data['email_batch']:
                email_addr = item.get('address')
                status = item.get('status', 'unknown')
                results_map[email_addr] = status
             
        return results_map
    except Exception as e:
        logger.error(f"Bulk API Exception: {e}")  
        return {}
