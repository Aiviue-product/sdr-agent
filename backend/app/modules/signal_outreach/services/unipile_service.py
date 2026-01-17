"""
Unipile Service
Handles all Unipile API interactions for LinkedIn DM messaging.

API Documentation: https://developer.unipile.com
"""
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

from app.shared.core.config import settings
from app.shared.core.constants import (
    TIMEOUT_UNIPILE_API,
    TIMEOUT_UNIPILE_PROFILE,
    TIMEOUT_UNIPILE_MESSAGE
)

logger = logging.getLogger("unipile_service")


class UnipileService:
    """
    Unipile API client for LinkedIn messaging.
    
    Provides methods for:
    - Getting user profile from LinkedIn URL
    - Sending connection requests
    - Creating chats and sending DMs
    """
    
    def __init__(self):
        self.api_key = settings.UNIPILE_API_KEY
        self.base_url = settings.UNIPILE_DSN
        self.account_id = settings.UNIPILE_ACCOUNT_ID
        
        if not self.api_key or not self.account_id:
            logger.warning("⚠️ Unipile credentials not configured. Set UNIPILE_API_KEY and UNIPILE_ACCOUNT_ID in .env")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for Unipile API requests."""
        return {
            "X-API-KEY": self.api_key,
            "accept": "application/json",
            "content-type": "application/json"
        }
    
    def _extract_public_identifier(self, linkedin_url: str) -> str:
        """
        Extract the public identifier from a LinkedIn URL.
        
        Examples:
        - https://www.linkedin.com/in/john-doe-123456/ -> john-doe-123456
        - https://linkedin.com/in/john-doe -> john-doe
        """
        # Remove trailing slash and extract the last segment
        url = linkedin_url.rstrip('/')
        parts = url.split('/in/')
        if len(parts) > 1:
            return parts[-1].split('/')[0].split('?')[0]
        return url.split('/')[-1]
    
    async def get_profile(self, linkedin_url: str) -> Dict[str, Any]:
        """
        Get user profile from LinkedIn URL.
        
        Returns provider_id, connection status, and profile info.
        
        Args:
            linkedin_url: Full LinkedIn profile URL
            
        Returns:
            Dict with success status, provider_id, connection_status, and profile data
        """
        try:
            public_identifier = self._extract_public_identifier(linkedin_url)
            
            async with httpx.AsyncClient(timeout=TIMEOUT_UNIPILE_PROFILE) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/users/{public_identifier}",
                    headers=self._get_headers(),
                    params={"account_id": self.account_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Map network_distance to connection_status
                    network_distance = data.get("network_distance", "")
                    if network_distance == "FIRST_DEGREE":
                        connection_status = "connected"
                    elif network_distance == "OUT_OF_NETWORK":
                        connection_status = "none"
                    else:
                        connection_status = "none"  # SECOND_DEGREE, THIRD_DEGREE
                    
                    return {
                        "success": True,
                        "provider_id": data.get("provider_id"),
                        "connection_status": connection_status,
                        "network_distance": network_distance,
                        "profile": {
                            "first_name": data.get("first_name"),
                            "last_name": data.get("last_name"),
                            "full_name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                            "headline": data.get("headline"),
                            "location": data.get("location"),
                            "profile_picture_url": data.get("profile_picture_url"),
                            "public_identifier": data.get("public_identifier"),
                            "is_premium": data.get("is_premium", False)
                        }
                    }
                else:
                    logger.error(f"❌ Get profile failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Failed to get profile: {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout getting profile for {linkedin_url}")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"❌ Error getting profile: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_connection_request(
        self, 
        provider_id: str, 
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a connection request to a LinkedIn user.
        
        Args:
            provider_id: Unipile's LinkedIn user ID
            message: Optional connection note (max 300 chars)
            
        Returns:
            Dict with success status and invitation_id
        """
        try:
            payload = {
                "account_id": self.account_id,
                "provider_id": provider_id
            }
            
            if message:
                # Truncate to 300 chars (LinkedIn limit)
                payload["message"] = message[:300]
            
            async with httpx.AsyncClient(timeout=TIMEOUT_UNIPILE_API) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/users/invite",
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"✅ Connection request sent: {data.get('invitation_id')}")
                    return {
                        "success": True,
                        "invitation_id": data.get("invitation_id"),
                        "sent_at": datetime.utcnow().isoformat()
                    }
                elif response.status_code == 422:
                    # Check for specific errors
                    error_data = response.json()
                    error_type = error_data.get("type", "")
                    
                    if "already_connected" in error_type:
                        return {
                            "success": False,
                            "error": "Already connected",
                            "already_connected": True
                        }
                    elif "already_invited" in error_type:
                        return {
                            "success": False,
                            "error": "Already invited recently",
                            "already_invited": True
                        }
                    else:
                        return {
                            "success": False,
                            "error": error_data.get("title", "Request failed"),
                            "details": error_data.get("detail")
                        }
                else:
                    logger.error(f"❌ Connection request failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Failed to send connection: {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout sending connection request")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"❌ Error sending connection: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_chat_and_send_dm(
        self, 
        provider_id: str, 
        message: str
    ) -> Dict[str, Any]:
        """
        Create a new chat and send a DM to a connected user.
        
        Args:
            provider_id: Unipile's LinkedIn user ID
            message: The message to send
            
        Returns:
            Dict with success status, chat_id, and message_id
        """
        try:
            payload = {
                "account_id": self.account_id,
                "attendees_ids": [provider_id],
                "text": message
            }
            
            async with httpx.AsyncClient(timeout=TIMEOUT_UNIPILE_MESSAGE) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/chats",
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"✅ DM sent successfully")
                    return {
                        "success": True,
                        "chat_id": data.get("chat_id"),
                        "message_id": data.get("message_id"),
                        "sent_at": datetime.utcnow().isoformat()
                    }
                elif response.status_code == 422:
                    error_data = response.json()
                    error_type = error_data.get("type", "")
                    
                    if "no_connection" in error_type or "user_unreachable" in error_type:
                        return {
                            "success": False,
                            "error": "Not connected - cannot send DM",
                            "not_connected": True
                        }
                    else:
                        return {
                            "success": False,
                            "error": error_data.get("title", "Failed to send DM"),
                            "details": error_data.get("detail")
                        }
                else:
                    logger.error(f"❌ Send DM failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Failed to send DM: {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout sending DM")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"❌ Error sending DM: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_message_to_chat(
        self, 
        chat_id: str, 
        message: str
    ) -> Dict[str, Any]:
        """
        Send a message to an existing chat.
        
        Args:
            chat_id: The Unipile chat ID
            message: The message to send
            
        Returns:
            Dict with success status and message_id
        """
        try:
            payload = {"text": message}
            
            async with httpx.AsyncClient(timeout=TIMEOUT_UNIPILE_MESSAGE) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/chats/{chat_id}/messages",
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"✅ Message sent to chat {chat_id}")
                    return {
                        "success": True,
                        "message_id": data.get("id"),
                        "sent_at": datetime.utcnow().isoformat()
                    }
                else:
                    logger.error(f"❌ Send message failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Failed to send message: {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout sending message")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"❌ Error sending message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_chat_by_attendee(self, provider_id: str) -> Dict[str, Any]:
        """
        Find an existing chat with a specific user.
        
        Args:
            provider_id: The Unipile provider ID of the user
            
        Returns:
            Dict with chat info if found
        """
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_UNIPILE_API) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/chats",
                    headers=self._get_headers(),
                    params={
                        "account_id": self.account_id,
                        "account_type": "LINKEDIN",
                        "limit": 100
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    chats = data.get("items", [])
                    
                    # Find chat with the target attendee
                    for chat in chats:
                        if chat.get("attendee_provider_id") == provider_id:
                            return {
                                "success": True,
                                "found": True,
                                "chat_id": chat.get("id"),
                                "read_only": chat.get("read_only", 0) == 1
                            }
                    
                    return {
                        "success": True,
                        "found": False
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get chats: {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error finding chat: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def is_configured(self) -> bool:
        """Check if Unipile service is properly configured."""
        return bool(self.api_key and self.account_id and self.base_url)


# Singleton instance
unipile_service = UnipileService()
