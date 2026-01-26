"""
WATI Client Service
Low-level API wrapper for WATI WhatsApp Business API.

API Documentation: https://docs.wati.io/reference/api-endpoints

Handles:
- Authentication via Bearer token
- Send template messages (with retry)
- Get message templates (with caching)
- Get message status
- Contact management

Retry Strategy:
- Max 3 attempts with exponential backoff (2s, 4s, 8s)
- Only retries on: Timeout, Connection errors, 5xx server errors
- Does NOT retry on: 4xx client errors (bad request, unauthorized, etc.)
"""
import logging
import httpx
from typing import Dict, Any, Optional, List

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)

from app.shared.core.config import settings
from app.modules.whatsapp_outreach.services.wati_cache import wati_cache

logger = logging.getLogger("wati_client")

# Timeout settings
TIMEOUT_WATI_API = 30.0
TIMEOUT_WATI_MESSAGE = 45.0

# Retry settings
MAX_RETRY_ATTEMPTS = 3
RETRY_MIN_WAIT_SECONDS = 2
RETRY_MAX_WAIT_SECONDS = 10


# ============================================
# CUSTOM EXCEPTIONS FOR RETRY LOGIC
# ============================================

class WATIRetryableError(Exception):
    """Exception that indicates the request should be retried."""
    pass


class WATINonRetryableError(Exception):
    """Exception that indicates the request should NOT be retried (client error)."""
    pass


# ============================================
# RETRY DECORATOR
# ============================================

def wati_retry():
    """
    Retry decorator for WATI API calls.
    
    Retries on:
    - WATIRetryableError (server errors, timeouts)
    - httpx.TimeoutException
    - httpx.ConnectError
    
    Does NOT retry on:
    - WATINonRetryableError (4xx client errors)
    - Other exceptions
    """
    return retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=1,
            min=RETRY_MIN_WAIT_SECONDS,
            max=RETRY_MAX_WAIT_SECONDS
        ),
        retry=retry_if_exception_type((
            WATIRetryableError,
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ConnectTimeout,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


class WATIClient:
    """
    WATI API client for WhatsApp messaging.
    
    Provides low-level methods for:
    - Sending template messages
    - Getting templates
    - Managing contacts
    - Checking message status
    """
    
    def __init__(self):
        self.api_token = settings.WATI_API_TOKEN
        self.api_endpoint = settings.WATI_API_ENDPOINT.rstrip('/')
        self.channel_number = settings.WATI_CHANNEL_NUMBER
        
        if not self.api_token:
            logger.warning("⚠️ WATI_API_TOKEN not configured in .env")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for WATI API requests."""
        # Handle token that may or may not have 'Bearer ' prefix
        token = self.api_token
        if token and token.startswith("Bearer "):
            auth_value = token  # Already has Bearer prefix
        else:
            auth_value = f"Bearer {token}"
        
        return {
            "Authorization": auth_value,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def is_configured(self) -> bool:
        """Check if WATI service is properly configured."""
        return bool(self.api_token and self.api_endpoint)
    
    # ============================================
    # TEMPLATE OPERATIONS (with caching)
    # ============================================
    
    async def get_templates(
        self, 
        page_size: int = 100, 
        page_number: int = 1,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get all message templates from WATI with caching.
        
        Args:
            page_size: Number of templates per page
            page_number: Page number for pagination
            force_refresh: If True, bypass cache and fetch from WATI
        
        Returns:
            Dict with success, templates list, and pagination info
        
        Caching:
            - Templates are cached for 5 minutes by default
            - Use force_refresh=True to bypass cache
            - Call wati_cache.invalidate_templates() to manually invalidate
        """
        # Check cache first (unless force refresh requested)
        if not force_refresh:
            cached_templates = wati_cache.get_templates()
            if cached_templates is not None:
                logger.debug(f"Templates served from cache: {len(cached_templates)} templates")
                return {
                    "success": True,
                    "templates": cached_templates,
                    "total": len(cached_templates),
                    "page": page_number,
                    "page_size": page_size,
                    "from_cache": True
                }
        
        # Fetch from WATI API
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_WATI_API) as client:
                response = await client.get(
                    f"{self.api_endpoint}/api/v1/getMessageTemplates",
                    headers=self._get_headers(),
                    params={
                        "pageSize": page_size,
                        "pageNumber": page_number
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    templates = data.get("messageTemplates", [])
                    
                    # Filter to only APPROVED templates
                    approved_templates = [
                        t for t in templates 
                        if t.get("status") == "APPROVED"
                    ]
                    
                    # Update cache
                    wati_cache.set_templates(approved_templates)
                    logger.info(f"Templates fetched from WATI and cached: {len(approved_templates)} templates")
                    
                    return {
                        "success": True,
                        "templates": approved_templates,
                        "total": data.get("link", {}).get("total", len(approved_templates)),
                        "page": page_number,
                        "page_size": page_size,
                        "from_cache": False
                    }
                else:
                    logger.error(f"Get templates failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Failed to get templates: {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.error("Timeout getting templates from WATI")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_template_by_name(self, template_name: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get a specific template by name with caching.
        
        Args:
            template_name: Name of the template to fetch
            force_refresh: If True, bypass cache and fetch from WATI
        
        Returns:
            Dict with success and template details
        
        Performance:
            - First checks the by-name cache (O(1) lookup)
            - Falls back to fetching all templates if not cached
            - Much faster than fetching all templates every time!
        """
        # Check by-name cache first (unless force refresh)
        if not force_refresh:
            cached_template = wati_cache.get_template_by_name(template_name)
            if cached_template is not None:
                logger.debug(f"Template '{template_name}' served from cache")
                return {
                    "success": True,
                    "template": cached_template,
                    "params": [p.get("paramName") for p in cached_template.get("customParams", [])],
                    "from_cache": True
                }
        
        # Fetch all templates (this will update the cache)
        templates_result = await self.get_templates(page_size=500, force_refresh=force_refresh)
        
        if not templates_result.get("success"):
            return templates_result
        
        # Search in fetched templates
        for template in templates_result.get("templates", []):
            if template.get("elementName") == template_name:
                return {
                    "success": True,
                    "template": template,
                    "params": [p.get("paramName") for p in template.get("customParams", [])],
                    "from_cache": False
                }
        
        return {
            "success": False,
            "error": f"Template '{template_name}' not found or not approved"
        }
    
    def invalidate_template_cache(self) -> None:
        """
        Invalidate the template cache.
        Call this when you know templates have changed in WATI.
        """
        wati_cache.invalidate_templates()
        logger.info("Template cache invalidated")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get current cache status for debugging/monitoring."""
        return wati_cache.get_status()
    
    # ============================================
    # MESSAGE OPERATIONS (with retry)
    # ============================================
    
    async def send_template_message(
        self,
        phone_number: str,
        template_name: str,
        parameters: List[Dict[str, str]],
        broadcast_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a template message to a phone number via WATI.
        
        Args:
            phone_number: Recipient phone (E.164 format without +, e.g., "919876543210")
            template_name: Name of the approved WATI template
            parameters: List of {"name": "...", "value": "..."} for template variables
            broadcast_name: Optional campaign/broadcast identifier
            
        Returns:
            Dict with success, phone_number, message_id, and delivery status
        
        Retry Behavior:
            - Retries up to 3 times on timeout/connection errors
            - Exponential backoff: 2s, 4s, 8s between retries
            - Does NOT retry on 4xx errors (invalid number, bad template, etc.)
        """
        try:
            return await self._send_template_message_with_retry(
                phone_number=phone_number,
                template_name=template_name,
                parameters=parameters,
                broadcast_name=broadcast_name
            )
        except RetryError as e:
            # All retries exhausted
            logger.error(f"All retries exhausted sending to {phone_number}: {str(e)}")
            return {
                "success": False,
                "phone_number": phone_number,
                "error": f"Failed after {MAX_RETRY_ATTEMPTS} attempts: Request timeout or connection error",
                "retries_exhausted": True
            }
        except WATINonRetryableError as e:
            # Client error - don't retry
            return {
                "success": False,
                "phone_number": phone_number,
                "error": str(e),
                "retryable": False
            }
        except Exception as e:
            logger.error(f"Unexpected error sending message: {str(e)}")
            return {"success": False, "phone_number": phone_number, "error": str(e)}
    
    @wati_retry()
    async def _send_template_message_with_retry(
        self,
        phone_number: str,
        template_name: str,
        parameters: List[Dict[str, str]],
        broadcast_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Internal method with retry decorator.
        Raises exceptions for retry logic to work.
        """
        payload = {
            "template_name": template_name,
            "parameters": parameters
        }
        
        if broadcast_name:
            payload["broadcast_name"] = broadcast_name
        
        async with httpx.AsyncClient(timeout=TIMEOUT_WATI_MESSAGE) as client:
            response = await client.post(
                f"{self.api_endpoint}/api/v1/sendTemplateMessage",
                headers=self._get_headers(),
                params={"whatsappNumber": phone_number},
                json=payload
            )
            
            # Handle response based on status code
            if response.status_code == 200:
                data = response.json()
                
                if data.get("result") is True:
                    logger.info(f"Template message sent to {phone_number}")
                    return {
                        "success": True,
                        "phone_number": phone_number,
                        "template_name": template_name,
                        "valid_whatsapp": data.get("validWhatsAppNumber", True),
                        "contact_id": data.get("contact", {}).get("id"),
                        "message_ids": data.get("model", {}).get("ids", [])
                    }
                else:
                    # WATI returned result=false - this is a client error, don't retry
                    error_msg = data.get("info", "Unknown error")
                    logger.error(f"Send failed (non-retryable): {error_msg}")
                    raise WATINonRetryableError(error_msg)
            
            elif 400 <= response.status_code < 500:
                # 4xx Client errors - don't retry
                logger.error(f"Client error {response.status_code}: {response.text}")
                raise WATINonRetryableError(f"Client error: {response.status_code}")
            
            elif response.status_code >= 500:
                # 5xx Server errors - retry
                logger.warning(f"Server error {response.status_code}, will retry...")
                raise WATIRetryableError(f"Server error: {response.status_code}")
            
            else:
                # Unexpected status code
                logger.error(f"Unexpected status {response.status_code}: {response.text}")
                raise WATINonRetryableError(f"Unexpected error: {response.status_code}")
    
    async def get_messages(
        self, 
        phone_number: str,
        page_size: int = 100,
        page_number: int = 1
    ) -> Dict[str, Any]:
        """
        Get message history for a phone number.
        
        Returns:
            Dict with success and messages list
        
        Retry Behavior:
            - Retries up to 3 times on timeout/connection errors
        """
        try:
            return await self._get_messages_with_retry(phone_number, page_size, page_number)
        except RetryError as e:
            logger.error(f"All retries exhausted getting messages for {phone_number}")
            return {"success": False, "error": "Failed after multiple retries"}
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @wati_retry()
    async def _get_messages_with_retry(
        self,
        phone_number: str,
        page_size: int,
        page_number: int
    ) -> Dict[str, Any]:
        """Internal method with retry decorator."""
        async with httpx.AsyncClient(timeout=TIMEOUT_WATI_API) as client:
            response = await client.get(
                f"{self.api_endpoint}/api/v1/getMessages/{phone_number}",
                headers=self._get_headers(),
                params={
                    "pageSize": page_size,
                    "pageNumber": page_number
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", {}).get("items", [])
                
                return {
                    "success": True,
                    "messages": messages,
                    "total": data.get("messages", {}).get("total", len(messages))
                }
            elif response.status_code >= 500:
                # Server error - retry
                raise WATIRetryableError(f"Server error: {response.status_code}")
            else:
                # Client error - don't retry
                return {
                    "success": False,
                    "error": f"Failed to get messages: {response.status_code}"
                }
    
    async def get_message_status(self, phone_number: str) -> Dict[str, Any]:
        """
        Get latest message status for a phone number.
        
        Returns:
            Dict with latest message status (SENT/DELIVERED/READ/FAILED)
        """
        messages_result = await self.get_messages(phone_number, page_size=1)
        
        if not messages_result.get("success"):
            return messages_result
        
        messages = messages_result.get("messages", [])
        if not messages:
            return {
                "success": True,
                "status": None,
                "message": "No messages found"
            }
        
        latest = messages[0]
        return {
            "success": True,
            "status": latest.get("statusString", "UNKNOWN"),
            "failed_detail": latest.get("failedDetail"),
            "message_id": latest.get("id"),
            "created_at": latest.get("created")
        }
    
    # ============================================
    # CONTACT OPERATIONS
    # ============================================
    
    async def add_contact(
        self,
        phone_number: str,
        name: str,
        custom_params: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Add or update a contact in WATI.
        
        Args:
            phone_number: Phone number (E.164 without +)
            name: Contact name
            custom_params: Optional list of {"name": "...", "value": "..."} for custom fields
            
        Returns:
            Dict with success and contact info
        """
        try:
            payload = {"name": name}
            
            if custom_params:
                payload["customParams"] = custom_params
            
            async with httpx.AsyncClient(timeout=TIMEOUT_WATI_API) as client:
                response = await client.post(
                    f"{self.api_endpoint}/api/v1/addContact/{phone_number}",
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("result") is True:
                        return {
                            "success": True,
                            "contact_id": data.get("contact", {}).get("id"),
                            "phone_number": phone_number
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("info", "Failed to add contact")
                        }
                else:
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error adding contact: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_contacts(
        self,
        page_size: int = 100,
        page_number: int = 1
    ) -> Dict[str, Any]:
        """
        Get all contacts from WATI.
        
        Returns:
            Dict with success and contacts list
        """
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_WATI_API) as client:
                response = await client.get(
                    f"{self.api_endpoint}/api/v1/getContacts",
                    headers=self._get_headers(),
                    params={
                        "pageSize": page_size,
                        "pageNumber": page_number
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "contacts": data.get("contact_list", []),
                        "total": data.get("link", {}).get("total", 0)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get contacts: {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error getting contacts: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ============================================
    # WEBHOOK OPERATIONS
    # ============================================
    # In your Frontend, add a small "Refresh Webhook" button in your Settings page that only Admins can see.
    # When you click that button, it calls the endpoint, uses the utilised logic in your client, and you're set.
    # When you deploy, manually add the webhook URL inside the WATI Dashboard one last time. Then, you can delete the 
    # update_wati_webhook.py
    # script and the 
    # create_webhook
    # function from your client file to keep your codebase lean and clean.
# TODO: sagar make it uncommented and use it later

    # async def create_webhook(
    #     self,
    #     webhook_url: str,
    #     event_types: List[str]
    # ) -> Dict[str, Any]:
    #     """
    #     Register a webhook endpoint with WATI.
        
    #     Args:
    #         webhook_url: Your backend webhook URL
    #         event_types: List of event types to subscribe to
    #             - "message" (all message events)
    #             - "templateMessageSent"
    #             - "messageDelivered"
    #             - "messageRead"
    #             - "templateMessageFailed"
    #             - "newContactMessageReceived"
                
    #     Returns:
    #         Dict with success and webhook info
    #     """
    #     try:
    #         payload = [{
    #             "phoneNumber": self.channel_number,
    #             "status": 1,  # 1 = Enabled
    #             "url": webhook_url,
    #             "eventTypes": event_types
    #         }]
            
    #         async with httpx.AsyncClient(timeout=TIMEOUT_WATI_API) as client:
    #             response = await client.post(
    #                 f"{self.api_endpoint}/api/v2/webhookEndpoints",
    #                 headers=self._get_headers(),
    #                 json=payload
    #             )
                
    #             if response.status_code == 200:
    #                 data = response.json()
    #                 if data.get("ok"):
    #                     logger.info(f"✅ Webhook registered: {webhook_url}")
    #                     return {
    #                         "success": True,
    #                         "webhooks": data.get("result", [])
    #                     }
    #                 else:
    #                     return {
    #                         "success": False,
    #                         "error": "Webhook registration failed"
    #                     }
    #             else:
    #                 return {
    #                     "success": False,
    #                     "error": f"API error: {response.status_code}"
    #                 }
                    
    #     except Exception as e:
    #         logger.error(f"❌ Error creating webhook: {str(e)}")
    #         return {"success": False, "error": str(e)}


# Singleton instance
wati_client = WATIClient()
