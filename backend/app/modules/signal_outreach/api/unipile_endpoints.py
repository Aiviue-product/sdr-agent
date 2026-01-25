"""
Unipile DM API Endpoints
Handles sending DMs, connection requests, and managing LinkedIn outreach.
"""
import logging
import asyncio
import hmac
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.shared.core.config import settings

from app.shared.db.session import get_db
from app.shared.utils.cache import (
    app_cache,
    CACHE_TTL_RATE_LIMITS,
    get_rate_limits_cache_key
)
from app.shared.core.constants import (
    LINKEDIN_DAILY_CONNECTION_LIMIT,
    LINKEDIN_DAILY_DM_LIMIT,
    LINKEDIN_BULK_DELAY_SECONDS
)
from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead
from app.modules.signal_outreach.models.linkedin_activity import LinkedInActivity
from app.modules.signal_outreach.services.unipile_service import unipile_service
from app.modules.signal_outreach.services.linkedin_outreach_service import LinkedInOutreachService
from app.modules.signal_outreach.api.schemas import (
    SendDMRequest,
    SendDMResponse,
    SendConnectionRequest,
    SendConnectionResponse,
    BulkSendRequest,
    BulkSendResponse,
    ActivitiesResponse,
    ActivityItem,
    RateLimitStatus
)

router = APIRouter()
logger = logging.getLogger("unipile_api")


# ============================================
# WEBHOOK SECURITY
# ============================================

def verify_webhook_auth(auth_header: str, secret: str) -> bool:
    """
    Verify the Unipile webhook authentication header.
    
    Unipile sends a custom 'Unipile-Auth' header with the secret value.
    We compare this against our configured secret.
    
    Args:
        auth_header: Value from Unipile-Auth header
        secret: Our configured webhook secret
        
    Returns:
        True if authentication is valid, False otherwise
    """
    if not secret:
        # If no secret configured, skip verification (backward compatible)
        return True
    
    if not auth_header:
        logger.warning("⚠️ Webhook received without Unipile-Auth header")
        return False
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(auth_header, secret)


# ============================================
# HELPER FUNCTIONS
# ============================================

async def get_daily_counts(db: AsyncSession) -> dict:
    """
    Get today's connection and DM counts.
    CACHED for 30 seconds to reduce DB load.
    """
    cache_key = get_rate_limits_cache_key()
    
    # Try cache first
    cached = app_cache.get(cache_key)
    if cached is not None:
        return cached
    
    today = date.today()
    
    # Count connections sent today
    connections_result = await db.execute(
        select(func.count()).select_from(LinkedInLead).where(
            and_(
                LinkedInLead.connection_sent_at != None,
                func.date(LinkedInLead.connection_sent_at) == today
            )
        )
    )
    connections_today = connections_result.scalar() or 0
    
    # Count DMs sent today
    dms_result = await db.execute(
        select(func.count()).select_from(LinkedInLead).where(
            and_(
                LinkedInLead.dm_sent_at != None,
                func.date(LinkedInLead.dm_sent_at) == today
            )
        )
    )
    dms_today = dms_result.scalar() or 0
    
    result = {
        "connections_today": connections_today,
        "dms_today": dms_today
    }
    
    # Cache the result
    app_cache.set(cache_key, result, ttl_seconds=CACHE_TTL_RATE_LIMITS)
    
    return result


async def create_activity(
    db: AsyncSession,
    lead_id: int,
    activity_type: str,
    message: Optional[str] = None,
    lead_name: Optional[str] = None,
    lead_linkedin_url: Optional[str] = None,
    extra_data: Optional[dict] = None
):
    """Create a new activity record."""
    activity = LinkedInActivity(
        lead_id=lead_id,
        activity_type=activity_type,
        message=message,
        lead_name=lead_name,
        lead_linkedin_url=lead_linkedin_url,
        extra_data=extra_data or {}
    )
    db.add(activity)
    await db.commit()
    return activity


# ============================================
# RATE LIMIT ENDPOINT
# ============================================

@router.get("/rate-limits", response_model=RateLimitStatus)
async def get_rate_limits(db: AsyncSession = Depends(get_db)):
    """
    Get current rate limit status for LinkedIn operations.
    Shows how many connections/DMs can still be sent today.
    """
    counts = await get_daily_counts(db)
    
    return RateLimitStatus(
        connections_sent_today=counts["connections_today"],
        connections_remaining=max(0, LINKEDIN_DAILY_CONNECTION_LIMIT - counts["connections_today"]),
        connections_limit=LINKEDIN_DAILY_CONNECTION_LIMIT,
        dms_sent_today=counts["dms_today"],
        dms_remaining=max(0, LINKEDIN_DAILY_DM_LIMIT - counts["dms_today"]),
        dms_limit=LINKEDIN_DAILY_DM_LIMIT
    )


# ============================================
# SEND DM ENDPOINT
# ============================================

@router.post("/leads/{lead_id}/send-dm", response_model=SendDMResponse)
async def send_dm_to_lead(
    lead_id: int,
    request: SendDMRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a DM to a lead.
    """
    if not unipile_service.is_configured():
        raise HTTPException(status_code=503, detail="Unipile service not configured")
    
    # Check rate limits
    counts = await get_daily_counts(db)
    if counts["dms_today"] >= LINKEDIN_DAILY_DM_LIMIT:
        return SendDMResponse(
            success=False,
            message="Daily DM limit reached",
            lead_id=lead_id,
            error=f"You've reached the daily limit of {LINKEDIN_DAILY_DM_LIMIT} DMs"
        )
    
    try:
        service = LinkedInOutreachService(db)
        result = await service.send_dm_to_lead(
            lead_id=lead_id,
            custom_message=request.message if request else None
        )
        
        if result["success"]:
            # Invalidate rate limits cache since count changed
            app_cache.invalidate(get_rate_limits_cache_key())
            return SendDMResponse(
                success=True,
                message=result["message"],
                lead_id=lead_id,
                dm_status="sent",
                sent_at=result.get("sent_at")
            )
        else:
            return SendDMResponse(
                success=False,
                message=result["message"] if "message" in result else "Failed to send DM",
                lead_id=lead_id,
                error=result.get("error")
            )
    except Exception as e:
        logger.error(f"Error in send_dm_to_lead: {e}")
        return SendDMResponse(
            success=False,
            message="Internal server error",
            lead_id=lead_id,
            error=str(e)
        )


# ============================================
# SEND CONNECTION REQUEST ENDPOINT
# ============================================

@router.post("/leads/{lead_id}/send-connection", response_model=SendConnectionResponse)
async def send_connection_to_lead(
    lead_id: int,
    request: SendConnectionRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a connection request to a lead.
    """
    if not unipile_service.is_configured():
        raise HTTPException(status_code=503, detail="Unipile service not configured")
    
    # Check rate limits
    counts = await get_daily_counts(db)
    if counts["connections_today"] >= LINKEDIN_DAILY_CONNECTION_LIMIT:
        return SendConnectionResponse(
            success=False,
            message="Daily connection limit reached",
            lead_id=lead_id,
            error=f"You've reached the daily limit of {LINKEDIN_DAILY_CONNECTION_LIMIT} connections"
        )
    
    try:
        service = LinkedInOutreachService(db)
        result = await service.send_connection_request(
            lead_id=lead_id,
            message=request.message if request else None
        )
        
        if result["success"]:
            # Invalidate rate limits cache since count changed
            app_cache.invalidate(get_rate_limits_cache_key())
            return SendConnectionResponse(
                success=True,
                message=result["message"],
                lead_id=lead_id,
                connection_status="connected" if result.get("already_connected") else "pending",
                sent_at=result.get("sent_at")
            )
        else:
            return SendConnectionResponse(
                success=False,
                message=result.get("message", "Failed to send connection request"),
                lead_id=lead_id,
                error=result.get("error")
            )
    except Exception as e:
        logger.error(f"Error in send_connection_to_lead: {e}")
        return SendConnectionResponse(
            success=False,
            message="Internal server error",
            lead_id=lead_id,
            error=str(e)
        )


# ============================================
# BULK SEND ENDPOINT
# ============================================

@router.post("/bulk-send", response_model=BulkSendResponse)
async def bulk_send(
    request: BulkSendRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send DMs or connection requests to multiple leads.
    
    Includes rate limiting and delays between sends.
    """
    if not unipile_service.is_configured():
        raise HTTPException(status_code=503, detail="Unipile service not configured")
    
    results = []
    successful = 0
    failed = 0
    
    for i, lead_id in enumerate(request.lead_ids):
        # Add delay between requests (except for first one)
        if i > 0:
            await asyncio.sleep(LINKEDIN_BULK_DELAY_SECONDS)
        
        try:
            if request.send_type == "connection":
                result = await send_connection_to_lead(
                    lead_id=lead_id,
                    request=SendConnectionRequest(message=request.message) if request.message else None,
                    db=db
                )
            else:
                result = await send_dm_to_lead(
                    lead_id=lead_id,
                    request=SendDMRequest(message=request.message) if request.message else None,
                    db=db
                )
            
            if result.success:
                successful += 1
            else:
                failed += 1
            
            results.append({
                "lead_id": lead_id,
                "success": result.success,
                "message": result.message,
                "error": result.error if hasattr(result, 'error') else None
            })
            
        except Exception as e:
            failed += 1
            results.append({
                "lead_id": lead_id,
                "success": False,
                "message": "Error",
                "error": str(e)
            })
    
    return BulkSendResponse(
        success=failed == 0,
        total=len(request.lead_ids),
        successful=successful,
        failed=failed,
        results=results
    )


# ============================================
# ACTIVITIES ENDPOINT
# ============================================

@router.get("/activities", response_model=ActivitiesResponse)
async def get_activities(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    activity_type: Optional[str] = Query(default=None),
    lead_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity timeline with pagination.
    
    Can filter by activity_type or lead_id.
    """
    # Build query
    query = select(LinkedInActivity).order_by(LinkedInActivity.created_at.desc())
    count_query = select(func.count()).select_from(LinkedInActivity)
    
    if activity_type:
        query = query.where(LinkedInActivity.activity_type == activity_type)
        count_query = count_query.where(LinkedInActivity.activity_type == activity_type)
    
    if lead_id:
        query = query.where(LinkedInActivity.lead_id == lead_id)
        count_query = count_query.where(LinkedInActivity.lead_id == lead_id)
    
    # Get total count
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # Convert to response format
    activity_items = [
        ActivityItem(
            id=a.id,
            lead_id=a.lead_id,
            activity_type=a.activity_type,
            message=a.message,
            lead_name=a.lead_name,
            lead_linkedin_url=a.lead_linkedin_url,
            created_at=a.created_at.isoformat() if a.created_at else ""
        )
        for a in activities
    ]
    
    return ActivitiesResponse(
        activities=activity_items,
        total_count=total_count,
        page=page,
        limit=limit,
        has_more=(offset + len(activities)) < total_count
    )


# ============================================
# WEBHOOK ENDPOINT
# ============================================

@router.post("/webhook")
async def unipile_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Unipile webhook events.
    
    Events:
    - message_received: Someone replied to a DM
    - new_relation: Connection request accepted
    
    Security:
    - If UNIPILE_WEBHOOK_SECRET is configured, verifies the Unipile-Auth header
    - Rejects requests with invalid auth (401 Unauthorized)
    """
    # Verify webhook authentication if secret is configured
    auth_header = request.headers.get("Unipile-Auth", "") or request.headers.get("unipile-auth", "")
    
    if not verify_webhook_auth(auth_header, settings.UNIPILE_WEBHOOK_SECRET):
        logger.warning("🚫 Webhook rejected: Invalid Unipile-Auth header")
        raise HTTPException(status_code=401, detail="Invalid webhook authentication")
    
    try:
        data = await request.json()
        event_type = data.get("event")
        
        logger.info(f"📬 Webhook received: {event_type}")
        
        service = LinkedInOutreachService(db)
        
        if event_type == "message_received":
            # Only process if we are NOT the sender (it's a reply)
            if data.get("is_sender") is False:
                sender = data.get("sender", {})
                provider_id = sender.get("attendee_provider_id")
                
                # Get message text
                message_data = data.get("message", "")
                message_text = message_data if isinstance(message_data, str) else message_data.get("text", "")
                
                if provider_id:
                    result = await service.handle_message_received(provider_id, message_text)
                    if not result.get("success"):
                        logger.warning(f"⚠️ Webhook processing failed: {result.get('error')}")
        
        elif event_type == "new_relation":
            # Connection accepted
            provider_id = data.get("provider_id") or data.get("user_provider_id")
            
            if provider_id:
                result = await service.handle_new_relation(provider_id)
                if not result.get("success"):
                    logger.warning(f"⚠️ Webhook processing failed: {result.get('error')}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        # Return 500 so webhook sender knows to retry
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

