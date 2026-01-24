"""
WATI Client Service
Low-level API wrapper for WATI WhatsApp Business API.

API Documentation: https://docs.wati.io/reference/api-endpoints

Handles:
- Authentication via Bearer token
- Send template messages
- Get message templates
- Get message status
- Contact management
"""
import logging
import httpx
from typing import Dict, Any, Optional, List

from app.shared.core.config import settings

logger = logging.getLogger("wati_client")

# Timeout settings
TIMEOUT_WATI_API = 30.0
TIMEOUT_WATI_MESSAGE = 45.0


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
    # TEMPLATE OPERATIONS
    # ============================================
    
    async def get_templates(
        self, 
        page_size: int = 100, 
        page_number: int = 1
    ) -> Dict[str, Any]:
        """
        Get all message templates from WATI.
        
        Returns:
            Dict with success, templates list, and pagination info
        """
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
                    
                    return {
                        "success": True,
                        "templates": approved_templates,
                        "total": data.get("link", {}).get("total", len(approved_templates)),
                        "page": page_number,
                        "page_size": page_size
                    }
                else:
                    logger.error(f"❌ Get templates failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Failed to get templates: {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.error("⏰ Timeout getting templates")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"❌ Error getting templates: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_template_by_name(self, template_name: str) -> Dict[str, Any]:
        """
        Get a specific template by name.
        
        Returns:
            Dict with success and template details
        """
        templates_result = await self.get_templates(page_size=500)
        
        if not templates_result.get("success"):
            return templates_result
        
        for template in templates_result.get("templates", []):
            if template.get("elementName") == template_name:
                return {
                    "success": True,
                    "template": template,
                    "params": [p.get("paramName") for p in template.get("customParams", [])]
                }
        
        return {
            "success": False,
            "error": f"Template '{template_name}' not found or not approved"
        }
    
    # ============================================
    # MESSAGE OPERATIONS
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
        """
        try:
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
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("result") is True:
                        logger.info(f"✅ Template message sent to {phone_number}")
                        return {
                            "success": True,
                            "phone_number": phone_number,
                            "template_name": template_name,
                            "valid_whatsapp": data.get("validWhatsAppNumber", True),
                            "contact_id": data.get("contact", {}).get("id"),
                            "message_ids": data.get("model", {}).get("ids", [])
                        }
                    else:
                        error_msg = data.get("info", "Unknown error")
                        logger.error(f"❌ Send failed: {error_msg}")
                        return {
                            "success": False,
                            "phone_number": phone_number,
                            "error": error_msg,
                            "details": data
                        }
                else:
                    logger.error(f"❌ Send failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "phone_number": phone_number,
                        "error": f"API error: {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout sending message to {phone_number}")
            return {"success": False, "phone_number": phone_number, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"❌ Error sending message: {str(e)}")
            return {"success": False, "phone_number": phone_number, "error": str(e)}
    
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
        """
        try:
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
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get messages: {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error getting messages: {str(e)}")
            return {"success": False, "error": str(e)}
    
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
    
    async def create_webhook(
        self,
        webhook_url: str,
        event_types: List[str]
    ) -> Dict[str, Any]:
        """
        Register a webhook endpoint with WATI.
        
        Args:
            webhook_url: Your backend webhook URL
            event_types: List of event types to subscribe to
                - "message" (all message events)
                - "templateMessageSent"
                - "messageDelivered"
                - "messageRead"
                - "templateMessageFailed"
                - "newContactMessageReceived"
                
        Returns:
            Dict with success and webhook info
        """
        try:
            payload = [{
                "phoneNumber": self.channel_number,
                "status": 1,  # 1 = Enabled
                "url": webhook_url,
                "eventTypes": event_types
            }]
            
            async with httpx.AsyncClient(timeout=TIMEOUT_WATI_API) as client:
                response = await client.post(
                    f"{self.api_endpoint}/api/v2/webhookEndpoints",
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        logger.info(f"✅ Webhook registered: {webhook_url}")
                        return {
                            "success": True,
                            "webhooks": data.get("result", [])
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Webhook registration failed"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error creating webhook: {str(e)}")
            return {"success": False, "error": str(e)}


# Singleton instance
wati_client = WATIClient()
