
import os
import requests
import logging
import json

logger = logging.getLogger("instantly_service") 

#  V2 Endpoint
INSTANTLY_API_URL = "https://api.instantly.ai/api/v2/leads"

def send_lead_to_instantly(lead_data: dict, emails_payload: any):
    """
    Adds a SINGLE lead to an Instantly.ai campaign using API V2.
    """
    api_key = os.environ.get("INSTANTLY_API_KEY")
    campaign_id = os.environ.get("INSTANTLY_CAMPAIGN_ID")

    if not api_key or not campaign_id:
        logger.error("❌ Missing Instantly API Key or Campaign ID")
        return {"error": "Server misconfiguration: Missing Instantly credentials"}

    user_email = lead_data.get("email")
    if not user_email:
        return {"error": "Lead has no email address."}

    # 1. Map Variables
    custom_vars = {
        "designation": lead_data.get("designation", ""), 
        "sector": lead_data.get("sector", "")
    }

    if isinstance(emails_payload, dict):
        # Sequence Mode (Purple Button)
        custom_vars["custom_message_1"] = emails_payload.get("email_1", "")
        custom_vars["custom_message_2"] = emails_payload.get("email_2", "")
        custom_vars["custom_message_3"] = emails_payload.get("email_3", "")
        personalization_value = emails_payload.get("email_1", "")
    else:
        # Single Send Mode (Small Button)
        custom_vars["custom_message"] = str(emails_payload)
        personalization_value = str(emails_payload)

    # 2. Prepare Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 3. Flattened Payload (No 'leads' array wrapper)
    payload = {
        "campaign": campaign_id,
        "email": user_email,
        "first_name": lead_data.get("first_name", ""),
        "last_name": lead_data.get("last_name", ""),
        "company_name": lead_data.get("company_name", ""), 
        "website": lead_data.get("website", ""),
        "personalization": personalization_value,
        "custom_variables": custom_vars
    }

    # --- DEBUG LOG ---
    logger.info("--- SENDING TO INSTANTLY V2 ---") 
    logger.info(f" Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(INSTANTLY_API_URL, json=payload, headers=headers)
        
        #  ADD THIS: Log the actual response
        logger.info(f" Response Status: {response.status_code}")
        logger.info(f" Response Body: {response.text}")
        
        if not response.ok:
            logger.error(f" Instantly Error: {response.status_code} - {response.text}")
            return {"error": f"Instantly Error: {response.text}"}

        response_data = response.json()
        
        #  ADD THIS: Check if lead was actually added
        if response_data:
            logger.info(f"Instantly Response Data: {json.dumps(response_data, indent=2)}")
        
        return {"success": True, "instantly_response": response_data}
        
    except Exception as e:
        logger.error(f" Connection Failed: {str(e)}") 
        return {"error": str(e)} 