"""
WhatsApp Outreach API Endpoints
Handles WhatsApp messaging, lead management, and WATI webhooks.
"""
import logging
import hmac
import hashlib
import secrets
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
    BulkSendWhatsAppRequest,  # Still used by check_bulk_eligibility
    CreateLeadRequest,
    UpdateLeadRequest,
    CreateBulkJobRequest,
    # Response schemas
    WhatsAppLeadSummary,
    WhatsAppLeadDetail,
    WhatsAppLeadsListResponse,
    WhatsAppMessageItem,
    ConversationResponse,
    SendWhatsAppResponse,
    BulkEligibilityResponse,
    TemplatesResponse,
    ActivitiesResponse,
    WhatsAppActivityItem,
    ImportResponse,
    WebhookResponse,
    BulkJobDetail,
    BulkJobsListResponse,
    BulkJobResponse,
    BulkJobItemsResponse,
)

router = APIRouter()
logger = logging.getLogger("whatsapp_api")


# ============================================
# WEBHOOK SECURITY
# ============================================

def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check for forwarded headers (when behind reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs; first is the client
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Direct connection
    return request.client.host if request.client else ""


def _is_ip_allowed(client_ip: str) -> bool:
    """Check if client IP is in the whitelist (if configured)."""
    allowed_ips = settings.WATI_WEBHOOK_ALLOWED_IPS
    
    # If no whitelist configured, allow all (rely on token auth)
    if not allowed_ips:
        return True
    
    # Parse comma-separated IPs
    whitelist = [ip.strip() for ip in allowed_ips.split(",") if ip.strip()]
    
    if not whitelist:
        return True
    
    return client_ip in whitelist


def verify_wati_webhook(request: Request) -> bool:
    """
    Verify WATI webhook authenticity using multiple security layers.
    
    Security layers:
    1. IP whitelist (if WATI_WEBHOOK_ALLOWED_IPS is configured)
    2. Secret token validation (if WATI_WEBHOOK_SECRET is configured)
    
    Returns True if verification passes, False otherwise.
    """
    client_ip = _get_client_ip(request)
    
    # Layer 1: IP Whitelist Check
    if not _is_ip_allowed(client_ip):
        logger.warning(f"Webhook rejected: IP {client_ip} not in whitelist")
        return False
    
    # Layer 2: Secret Token Validation
    webhook_secret = settings.WATI_WEBHOOK_SECRET
    
    if webhook_secret:
        # Check for secret in header (custom header approach)
        provided_token = request.headers.get("X-Webhook-Secret") or request.headers.get("Authorization")
        
        if not provided_token:
            logger.warning(f"Webhook rejected: Missing authentication header from {client_ip}")
            return False
        
        # Remove 'Bearer ' prefix if present
        if provided_token.startswith("Bearer "):
            provided_token = provided_token[7:]
        
        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(provided_token, webhook_secret):
            logger.warning(f"Webhook rejected: Invalid secret token from {client_ip}")
            return False
    else:
        # No secret configured - log warning in production
        logger.warning("WATI_WEBHOOK_SECRET not configured - webhook authentication disabled")
    
    logger.debug(f"Webhook verified successfully from {client_ip}")
    return True


# ============================================
# CONFIGURATION ENDPOINT
# ============================================

def _mask_sensitive_string(value: str, show_chars: int = 4) -> str:
    """
    Mask a sensitive string, showing only first few characters.
    Example: "919876543210" -> "9198****"
    """
    if not value:
        return ""
    if len(value) <= show_chars:
        return "*" * len(value)
    return value[:show_chars] + "*" * (len(value) - show_chars)


@router.get("/config", summary="Check WhatsApp configuration status")
async def get_config_status():
    """
    Check if WATI API is properly configured.
    
    Returns:
        - configured: Whether WATI credentials are set
        - channel_configured: Whether channel number is set (masked for security)
        - webhook_auth_enabled: Whether webhook authentication is enabled
        - cache_status: Current template cache status
    
    Note: Sensitive values are masked for security.
    """
    from app.modules.whatsapp_outreach.services.wati_client import wati_client
    
    is_configured = wati_client.is_configured()
    channel = settings.WATI_CHANNEL_NUMBER
    
    return {
        "configured": is_configured,
        "channel_configured": bool(channel),
        # Show masked channel for debugging (e.g., "9198****" instead of full number)
        "channel_hint": _mask_sensitive_string(channel, 4) if channel else None,
        "webhook_auth_enabled": bool(settings.WATI_WEBHOOK_SECRET),
        "cache_status": wati_client.get_cache_status() if is_configured else None
    }


# ============================================
# TEMPLATES ENDPOINT
# ============================================

@router.get("/templates", response_model=TemplatesResponse, summary="Get available WhatsApp templates")
async def get_templates(
    refresh: bool = Query(default=False, description="Force refresh from WATI (bypass cache)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all approved WATI templates.
    
    Returns simplified template info for UI dropdown.
    
    Caching:
    - Templates are cached for 5 minutes
    - Use ?refresh=true to force fetch from WATI
    """
    service = WhatsAppOutreachService(db)
    
    if not service.is_configured():
        raise HTTPException(status_code=503, detail="WATI API not configured")
    
    result = await service.get_available_templates(force_refresh=refresh)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to fetch templates"))
    
    return TemplatesResponse(
        success=True,
        templates=result.get("templates", []),
        total=result.get("total", 0)
    )


@router.get("/cache/status", summary="Get WATI cache status")
async def get_cache_status():
    """
    Get current status of the WATI template cache.
    
    Useful for debugging and monitoring cache behavior.
    """
    from app.modules.whatsapp_outreach.services.wati_client import wati_client
    
    return {
        "cache": wati_client.get_cache_status(),
        "message": "Use /templates?refresh=true to force refresh"
    }


@router.post("/cache/invalidate", summary="Invalidate WATI cache")
async def invalidate_cache():
    """
    Manually invalidate the WATI template cache.
    
    Use this when you've updated templates in WATI dashboard
    and want to see changes immediately without waiting for TTL expiry.
    """
    from app.modules.whatsapp_outreach.services.wati_client import wati_client
    
    wati_client.invalidate_template_cache()
    
    return {
        "success": True,
        "message": "Template cache invalidated. Next request will fetch fresh data from WATI."
    }


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


@router.post("/sync-all", summary="Sync all data with WATI")
async def sync_all_data(db: AsyncSession = Depends(get_db)):
    """
    Perform a deep sync:
    1. Refresh templates from WATI
    2. Sync delivery status for all active leads
    3. Fetch new messages (sent and received)
    """
    service = WhatsAppOutreachService(db)
    result = await service.sync_all_wati_data()
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Sync failed"))
        
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


# ============================================
# BULK JOB OPERATIONS (with job tracking)
# ============================================

@router.post("/bulk/jobs", response_model=BulkJobResponse, summary="Create a bulk send job")
async def create_bulk_job(
    request: CreateBulkJobRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new bulk send job with tracking.
    
    This creates a job that can be:
    - Started immediately (if start_immediately=true)
    - Started later via POST /bulk/jobs/{job_id}/start
    - Resumed if interrupted
    - Paused and cancelled
    
    Benefits over /bulk/send:
    - Job persists even if server crashes
    - Can resume from where it stopped
    - Progress tracking in real-time
    - Can pause and cancel
    """
    service = WhatsAppOutreachService(db)
    
    if not service.is_configured():
        raise HTTPException(status_code=503, detail="WATI API not configured")
    
    # Create the job
    result = await service.create_bulk_job(
        lead_ids=request.lead_ids,
        template_name=request.template_name,
        broadcast_name=request.broadcast_name
    )
    
    if not result.get("success"):
        # Return 400 for validation errors (missing leads), 500 for server errors
        status_code = 400 if result.get("missing_ids") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error"))
    
    # Start immediately if requested
    if request.start_immediately:
        job_id = result["job"]["id"]
        process_result = await service.process_bulk_job(job_id)
        return BulkJobResponse(
            success=process_result.get("success", False),
            job=BulkJobDetail(**process_result["job"]) if process_result.get("job") else None,
            message=process_result.get("message"),
            error=process_result.get("error"),
            sent=process_result.get("sent"),
            failed=process_result.get("failed"),
            can_resume=process_result.get("can_resume")
        )
    
    return BulkJobResponse(
        success=True,
        job=BulkJobDetail(**result["job"]),
        message=result.get("message")
    )


@router.get("/bulk/jobs", response_model=BulkJobsListResponse, summary="List all bulk jobs")
async def list_bulk_jobs(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all bulk send jobs with optional status filter.
    
    Status values: pending, running, paused, completed, failed, cancelled
    """
    service = WhatsAppOutreachService(db)
    result = await service.get_bulk_jobs(status=status, skip=skip, limit=limit)
    
    return BulkJobsListResponse(
        success=True,
        jobs=[BulkJobDetail(**j) for j in result["jobs"]],
        total=result["total"],
        skip=skip,
        limit=limit
    )


@router.get("/bulk/jobs/{job_id}", response_model=BulkJobResponse, summary="Get bulk job details")
async def get_bulk_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get details of a specific bulk job."""
    service = WhatsAppOutreachService(db)
    result = await service.get_bulk_job(job_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return BulkJobResponse(
        success=True,
        job=BulkJobDetail(**result["job"])
    )


@router.get("/bulk/jobs/{job_id}/items", response_model=BulkJobItemsResponse, summary="Get bulk job items")
async def get_bulk_job_items(
    job_id: int,
    status: Optional[str] = Query(default=None, description="Filter by item status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get individual items for a bulk job.
    
    Item status values: pending, processing, sent, failed, skipped
    """
    service = WhatsAppOutreachService(db)
    result = await service.get_bulk_job_items(
        job_id=job_id,
        status=status,
        skip=skip,
        limit=limit
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    from app.modules.whatsapp_outreach.schemas.whatsapp_schemas import BulkJobItem
    
    return BulkJobItemsResponse(
        success=True,
        items=[BulkJobItem(**item) for item in result["items"]],
        job=BulkJobDetail(**result["job"]) if result.get("job") else None
    )


@router.post("/bulk/jobs/{job_id}/start", response_model=BulkJobResponse, summary="Start/resume a bulk job")
async def start_bulk_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Start or resume a bulk job.
    
    Can be used to:
    - Start a pending job
    - Resume a paused job
    - Retry a failed job (continues from where it stopped)
    """
    service = WhatsAppOutreachService(db)
    
    if not service.is_configured():
        raise HTTPException(status_code=503, detail="WATI API not configured")
    
    result = await service.process_bulk_job(job_id)
    
    return BulkJobResponse(
        success=result.get("success", False),
        job=BulkJobDetail(**result["job"]) if result.get("job") else None,
        message=result.get("message"),
        error=result.get("error"),
        sent=result.get("sent"),
        failed=result.get("failed"),
        can_resume=result.get("can_resume")
    )


@router.post("/bulk/jobs/{job_id}/pause", response_model=BulkJobResponse, summary="Pause a bulk job")
async def pause_bulk_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Pause a running bulk job.
    
    Can be resumed later via POST /bulk/jobs/{job_id}/start
    """
    service = WhatsAppOutreachService(db)
    result = await service.pause_bulk_job(job_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return BulkJobResponse(
        success=True,
        job=BulkJobDetail(**result["job"]),
        message=result.get("message")
    )


@router.post("/bulk/jobs/{job_id}/cancel", response_model=BulkJobResponse, summary="Cancel a bulk job")
async def cancel_bulk_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Cancel a bulk job permanently.
    
    Cannot be resumed after cancellation.
    """
    service = WhatsAppOutreachService(db)
    result = await service.cancel_bulk_job(job_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return BulkJobResponse(
        success=True,
        job=BulkJobDetail(**result["job"]),
        message=result.get("message")
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
    
    Security:
    - IP whitelist validation (if WATI_WEBHOOK_ALLOWED_IPS configured)
    - Secret token validation (if WATI_WEBHOOK_SECRET configured)
    
    Supported events:
    - templateMessageSent: Message sent successfully
    - messageDelivered: Message delivered to device
    - messageRead: Message read by recipient  
    - templateMessageFailed: Message delivery failed
    - message: Inbound reply from lead
    """
    # Security verification
    if not verify_wati_webhook(request):
        logger.error(f"Unauthorized webhook attempt from {_get_client_ip(request)}")
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized webhook request"
        )
    
    # Parse JSON payload
    try:
        event_data = await request.json()
    except Exception as e:
        logger.error(f"Invalid webhook JSON payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Log webhook receipt (without emoji for production logging)
    event_type = event_data.get('eventType', 'unknown')
    wa_id = event_data.get('waId', 'unknown')
    logger.info(f"Webhook received: type={event_type}, waId={wa_id}")
    
    # Process the webhook event
    service = WhatsAppOutreachService(db)
    result = await service.handle_webhook_event(event_data)
    
    # Log processing result
    if result.get("success"):
        logger.info(f"Webhook processed successfully: type={event_type}, lead_id={result.get('lead_id')}")
    else:
        logger.warning(f"Webhook processing failed: type={event_type}, error={result.get('error')}")
    
    return WebhookResponse(**result)
