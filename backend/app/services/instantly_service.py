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
        # We map BODIES to custom_message_X
        custom_vars["custom_message_1"] = emails_payload.get("email_1", "")
        custom_vars["custom_message_2"] = emails_payload.get("email_2", "")
        custom_vars["custom_message_3"] = emails_payload.get("email_3", "")
        
        # We map SUBJECTS to subject_X
        custom_vars["subject_1"] = emails_payload.get("email_1_subject", "")
        custom_vars["subject_2"] = emails_payload.get("email_2_subject", "")
        custom_vars["subject_3"] = emails_payload.get("email_3_subject", "")
        
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
        
        # Log the actual response
        logger.info(f" Response Status: {response.status_code}")
        logger.info(f" Response Body: {response.text}")
        
        if not response.ok:
            logger.error(f" Instantly Error: {response.status_code} - {response.text}")
            return {"error": f"Instantly Error: {response.text}"}

        response_data = response.json()
        
        #  Check if lead was actually added
        if response_data:
            logger.info(f"Instantly Response Data: {json.dumps(response_data, indent=2)}")
        
        return {"success": True, "instantly_response": response_data}
        
    except Exception as e:
        logger.error(f" Connection Failed: {str(e)}") 
        return {"error": str(e)}


# ============================================
# BULK PUSH FUNCTION (NEW)
# ============================================
INSTANTLY_BULK_API_URL = "https://api.instantly.ai/api/v2/leads/add"

def send_leads_bulk_to_instantly(leads_data: list):
    """
    Adds MULTIPLE leads (up to 100) to an Instantly.ai campaign using API V2 Bulk Endpoint.
    
    Args:
        leads_data: List of lead dictionaries, each containing:
            - email, first_name, last_name, company_name
            - email_1_subject, email_1_body, email_2_subject, email_2_body, ...
            - personalized_intro (optional)
    
    Returns:
        dict with success/failure metrics from Instantly
    """
    api_key = os.environ.get("INSTANTLY_API_KEY")
    campaign_id = os.environ.get("INSTANTLY_CAMPAIGN_ID")

    if not api_key or not campaign_id:
        logger.error("❌ Missing Instantly API Key or Campaign ID")
        return {"error": "Server misconfiguration: Missing Instantly credentials"}

    if not leads_data:
        return {"error": "No leads provided"}

    # Build the leads array for bulk API
    leads_payload = []
    skipped_no_email = []

    for lead in leads_data:
        user_email = lead.get("email")
        
        # Skip leads without email
        if not user_email:
            skipped_no_email.append(lead.get("id", "unknown"))
            continue

        # Build custom variables with email subjects and bodies
        custom_vars = {
            "designation": lead.get("designation", ""),
            "sector": lead.get("sector", ""),
            # Email Bodies
            "custom_message_1": lead.get("email_1_body", ""),
            "custom_message_2": lead.get("email_2_body", ""),
            "custom_message_3": lead.get("email_3_body", ""),
            # Email Subjects
            "subject_1": lead.get("email_1_subject", ""),
            "subject_2": lead.get("email_2_subject", ""),
            "subject_3": lead.get("email_3_subject", ""),
        }

        # Use personalized intro as the personalization field, or fallback to first email body
        personalization_value = lead.get("personalized_intro") or lead.get("email_1_body", "")

        lead_obj = {
            "email": user_email,
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "company_name": lead.get("company_name", ""),
            "personalization": personalization_value,
            "custom_variables": custom_vars
        }
        leads_payload.append(lead_obj)

    if not leads_payload:
        return {"error": "No valid leads with email addresses", "skipped_no_email": skipped_no_email}

    # Prepare request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "campaign_id": campaign_id,
        "skip_if_in_workspace": True,  # Don't duplicate if already exists
        "leads": leads_payload
    }

    # Debug log
    logger.info("--- BULK SENDING TO INSTANTLY V2 ---")
    logger.info(f"📦 Total leads in payload: {len(leads_payload)}")

    try:
        response = requests.post(INSTANTLY_BULK_API_URL, json=payload, headers=headers)

        logger.info(f"📡 Response Status: {response.status_code}")
        logger.info(f"📄 Response Body: {response.text}")

        if not response.ok:
            logger.error(f"❌ Instantly Bulk Error: {response.status_code} - {response.text}")
            return {"error": f"Instantly Error: {response.text}"}

        response_data = response.json()

        # Build result summary
        result = {
            "success": True,
            "total_sent": response_data.get("total_sent", 0),
            "leads_uploaded": response_data.get("leads_uploaded", 0),
            "duplicated_leads": response_data.get("duplicated_leads", 0),
            "skipped_count": response_data.get("skipped_count", 0),
            "invalid_email_count": response_data.get("invalid_email_count", 0),
            "in_blocklist": response_data.get("in_blocklist", 0),
            "skipped_no_email_local": skipped_no_email,  # Leads we skipped before sending
            "instantly_response": response_data
        }

        logger.info(f"✅ Bulk push complete: {result['leads_uploaded']} uploaded")
        return result

    except Exception as e:
        logger.error(f"❌ Bulk Connection Failed: {str(e)}")
        return {"error": str(e)} 