"""
WhatsApp Outreach API Endpoints
Handles WhatsApp messaging, lead management, and WATI webhooks.
"""
import logging
import hmac
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.core.config import settings
from app.shared.db.session import get_db
from app.modules.whatsapp_outreach.services.whatsapp_service import WhatsAppOutreachService
from app.modules.whatsapp_outreach.repositories.whatsapp_lead_repository import WhatsAppLeadRepository
from app.modules.whatsapp_outreach.repositories.whatsapp_message_repository import WhatsAppMessageRepository
from app.modules.whatsapp_outreach.repositories.whatsapp_activity_repository import WhatsAppActivityRepository
from app.modules.whatsapp_outreach.schemas.whatsapp_schemas import (
    # Request schemas
    SendWhatsAppRequest,
    BulkSendWhatsAppRequest,
    CreateLeadRequest,
    UpdateLeadRequest,
    # Response schemas
    WhatsAppLeadSummary,
    WhatsAppLeadDetail,
    WhatsAppLeadsListResponse,
    WhatsAppMessageItem,
    ConversationResponse,
    SendWhatsAppResponse,
    BulkSendWhatsAppResponse,
    BulkEligibilityResponse,
    TemplatesResponse,
    ActivitiesResponse,
    WhatsAppActivityItem,
    ImportResponse,
    WebhookResponse,
)

router = APIRouter()
logger = logging.getLogger("whatsapp_api")


# ============================================
# WEBHOOK SECURITY
# ============================================

def verify_wati_webhook(request: Request) -> bool:
    """
    Verify WATI webhook authenticity.
    
    WATI uses a token-based auth in headers.
    For now, we'll check for a custom header if configured.
    """
    # WATI doesn't have standard webhook signing yet
    # Implement IP whitelist or header check if needed
    return True


# ============================================
# CONFIGURATION ENDPOINT
# ============================================

@router.get("/config", summary="Check WhatsApp configuration status")
async def get_config_status():
    """Check if WATI API is properly configured."""
    from app.modules.whatsapp_outreach.services.wati_client import wati_client
    
    return {
        "configured": wati_client.is_configured(),
        "endpoint": settings.WATI_API_ENDPOINT if wati_client.is_configured() else None,
        "channel": settings.WATI_CHANNEL_NUMBER if wati_client.is_configured() else None
    }


# ============================================
# TEMPLATES ENDPOINT
# ============================================

@router.get("/templates", response_model=TemplatesResponse, summary="Get available WhatsApp templates")
async def get_templates(db: AsyncSession = Depends(get_db)):
    """
    Get all approved WATI templates.
    
    Returns simplified template info for UI dropdown.
    """
    service = WhatsAppOutreachService(db)
    
    if not service.is_configured():
        raise HTTPException(status_code=503, detail="WATI API not configured")
    
    result = await service.get_available_templates()
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to fetch templates"))
    
    return TemplatesResponse(
        success=True,
        templates=result.get("templates", []),
        total=result.get("total", 0)
    )


# ============================================
# LEADS ENDPOINTS
# ============================================

@router.get("/leads", response_model=WhatsAppLeadsListResponse, summary="List all WhatsApp leads")
async def get_leads(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    source: Optional[str] = Query(default=None, description="Filter by source: manual, email_import, linkedin_import"),
    is_sent: Optional[bool] = Query(default=None, description="Filter by sent status"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of WhatsApp leads.
    
    Supports filtering by source and sent status.
    """
    repo = WhatsAppLeadRepository(db)
    
    leads = await repo.get_all_leads(
        source=source,
        is_sent=is_sent,
        skip=skip,
        limit=limit
    )
    
    total = await repo.get_total_count(source=source, is_sent=is_sent)
    
    return WhatsAppLeadsListResponse(
        leads=[WhatsAppLeadSummary(**lead) for lead in leads],
        total_count=total,
        skip=skip,
        limit=limit
    )


@router.get("/leads/{lead_id}", response_model=WhatsAppLeadDetail, summary="Get lead details")
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Get full details for a specific lead."""
    repo = WhatsAppLeadRepository(db)
    
    lead = await repo.get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return WhatsAppLeadDetail(**lead)


@router.post("/leads", response_model=WhatsAppLeadDetail, summary="Create a new lead")
async def create_lead(request: CreateLeadRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new WhatsApp lead manually.
    
    Phone number will be normalized to E.164 format.
    """
    repo = WhatsAppLeadRepository(db)
    activity_repo = WhatsAppActivityRepository(db)
    
    # Check if already exists
    existing = await repo.get_by_mobile(request.mobile_number)
    if existing:
        raise HTTPException(
            status_code=409, 
            detail=f"Lead with phone {request.mobile_number} already exists"
        )
    
    lead_data = request.model_dump()
    lead_data["source"] = "manual"
    
    try:
        lead = await repo.create_lead(lead_data)
        await db.commit()
        
        # Log activity
        await activity_repo.log_lead_created(
            lead_id=lead["id"],
            lead_name=lead["first_name"],
            lead_mobile=lead["mobile_number"],
            source="manual"
        )
        await db.commit()
        
        return WhatsAppLeadDetail(**lead)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/leads/{lead_id}", response_model=WhatsAppLeadDetail, summary="Update a lead")
async def update_lead(
    lead_id: int, 
    request: UpdateLeadRequest, 
    db: AsyncSession = Depends(get_db)
):
    """Update a WhatsApp lead's information."""
    repo = WhatsAppLeadRepository(db)
    
    # Check exists
    existing = await repo.get_by_id(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = request.model_dump(exclude_unset=True)
    
    try:
        lead = await repo.update_lead(lead_id, update_data)
        await db.commit()
        return WhatsAppLeadDetail(**lead)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/leads/{lead_id}", summary="Delete a lead")
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a WhatsApp lead and all related messages/activities."""
    repo = WhatsAppLeadRepository(db)
    
    deleted = await repo.delete_lead(lead_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"success": True, "message": "Lead deleted"}


# ============================================
# MESSAGE ENDPOINTS
# ============================================

@router.post("/leads/{lead_id}/send", response_model=SendWhatsAppResponse, summary="Send WhatsApp to lead")
async def send_whatsapp(
    lead_id: int,
    request: SendWhatsAppRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a WhatsApp template message to a single lead.
    
    Uses WATI API to send the message and tracks delivery status.
    """
    service = WhatsAppOutreachService(db)
    
    if not service.is_configured():
        raise HTTPException(status_code=503, detail="WATI API not configured")
    
    result = await service.send_message_to_lead(
        lead_id=lead_id,
        template_name=request.template_name,
        custom_params=request.custom_params,
        broadcast_name=request.broadcast_name
    )
    
    return SendWhatsAppResponse(
        success=result.get("success", False),
        message="Message sent" if result.get("success") else "Failed to send",
        lead_id=lead_id,
        phone_number=result.get("phone_number"),
        template_name=result.get("template_name"),
        status=result.get("status"),
        error=result.get("error")
    )


@router.get("/leads/{lead_id}/messages", response_model=ConversationResponse, summary="Get message history")
async def get_lead_messages(
    lead_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history for a lead."""
    lead_repo = WhatsAppLeadRepository(db)
    message_repo = WhatsAppMessageRepository(db)
    
    # Verify lead exists
    lead = await lead_repo.get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    messages = await message_repo.get_messages_for_lead(lead_id, skip=skip, limit=limit)
    total = await message_repo.get_messages_count_for_lead(lead_id)
    
    return ConversationResponse(
        messages=[WhatsAppMessageItem(**m) for m in messages],
        total_count=total,
        lead_id=lead_id
    )


@router.post("/leads/{lead_id}/sync-status", summary="Sync message status from WATI")
async def sync_message_status(lead_id: int, db: AsyncSession = Depends(get_db)):
    """
    Sync latest message status from WATI for a lead.
    
    Useful for manual refresh if webhook missed an update.
    """
    service = WhatsAppOutreachService(db)
    
    result = await service.sync_message_status(lead_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


# ============================================
# BULK OPERATIONS
# ============================================

@router.post("/bulk/check", response_model=BulkEligibilityResponse, summary="Check bulk eligibility")
async def check_bulk_eligibility(
    request: BulkSendWhatsAppRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Check which leads are eligible for WhatsApp messaging.
    
    Returns lists of eligible and ineligible leads with reasons.
    """
    service = WhatsAppOutreachService(db)
    
    result = await service.bulk_check_eligibility(request.lead_ids)
    
    return BulkEligibilityResponse(**result)


@router.post("/bulk/send", response_model=BulkSendWhatsAppResponse, summary="Bulk send WhatsApp messages")
async def bulk_send_whatsapp(
    request: BulkSendWhatsAppRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send WhatsApp messages to multiple leads.
    
    Includes rate limiting with delays between sends.
    """
    service = WhatsAppOutreachService(db)
    
    if not service.is_configured():
        raise HTTPException(status_code=503, detail="WATI API not configured")
    
    result = await service.bulk_send_messages(
        lead_ids=request.lead_ids,
        template_name=request.template_name,
        broadcast_name=request.broadcast_name
    )
    
    return BulkSendWhatsAppResponse(
        success=result.get("success", False),
        broadcast_name=result.get("broadcast_name", ""),
        total=len(request.lead_ids),
        success_count=result.get("success_count", 0),
        failed_count=result.get("failed_count", 0),
        results=result.get("results", [])
    )


# ============================================
# IMPORT ENDPOINTS
# ============================================

@router.post("/import/email-leads", response_model=ImportResponse, summary="Import from email leads")
async def import_from_email(db: AsyncSession = Depends(get_db)):
    """
    Import leads from email outreach module.
    
    Only imports leads that have a mobile number.
    Uses upsert to avoid duplicates.
    """
    service = WhatsAppOutreachService(db)
    
    result = await service.import_from_email_leads(db)
    
    return ImportResponse(**result)


@router.post("/import/linkedin-leads", response_model=ImportResponse, summary="Import from LinkedIn leads")
async def import_from_linkedin(db: AsyncSession = Depends(get_db)):
    """
    Import leads from LinkedIn outreach module.
    
    Note: LinkedIn leads typically don't have mobile numbers by default.
    Enrichment may be required first.
    """
    service = WhatsAppOutreachService(db)
    
    result = await service.import_from_linkedin_leads(db)
    
    return ImportResponse(**result)


# ============================================
# ACTIVITIES ENDPOINT
# ============================================

@router.get("/activities", response_model=ActivitiesResponse, summary="Get activities timeline")
async def get_activities(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    activity_type: Optional[str] = Query(default=None),
    lead_id: Optional[int] = Query(default=None),
    global_only: Optional[bool] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get WhatsApp activity timeline with pagination.
    
    Can filter by activity_type, lead_id, or global_only.
    """
    repo = WhatsAppActivityRepository(db)
    
    skip = (page - 1) * limit
    
    if lead_id:
        activities = await repo.get_activities_for_lead(lead_id, skip=skip, limit=limit)
        total = await repo.get_total_count(lead_id=lead_id)
    elif global_only:
        activities = await repo.get_global_activities(
            activity_type=activity_type,
            skip=skip,
            limit=limit
        )
        total = await repo.get_total_count(activity_type=activity_type, global_only=True)
    else:
        activities = await repo.get_all_activities(
            activity_type=activity_type,
            skip=skip,
            limit=limit
        )
        total = await repo.get_total_count(activity_type=activity_type)
    
    return ActivitiesResponse(
        activities=[WhatsAppActivityItem(**a) for a in activities],
        total_count=total,
        page=page,
        limit=limit,
        has_more=(skip + limit) < total
    )


# ============================================
# WEBHOOK ENDPOINT
# ============================================

@router.post("/webhook", response_model=WebhookResponse, summary="WATI webhook handler")
async def wati_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle incoming WATI webhook events.
    
    Supported events:
    - templateMessageSent: Message sent successfully
    - messageDelivered: Message delivered to device
    - messageRead: Message read by recipient  
    - templateMessageFailed: Message delivery failed
    - message: Inbound reply from lead
    """
    # Verify webhook (if implemented)
    if not verify_wati_webhook(request):
        raise HTTPException(status_code=401, detail="Unauthorized webhook request")
    
    try:
        event_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    logger.info(f"📬 Webhook received: {event_data.get('eventType', 'unknown')}")
    
    service = WhatsAppOutreachService(db)
    
    result = await service.handle_webhook_event(event_data)
    
    return WebhookResponse(**result)
