"""
Unipile DM API Endpoints
Handles sending DMs, connection requests, and managing LinkedIn outreach.
"""
import logging
import asyncio
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.shared.db.session import get_db
from app.shared.core.constants import (
    LINKEDIN_DAILY_CONNECTION_LIMIT,
    LINKEDIN_DAILY_DM_LIMIT,
    LINKEDIN_BULK_DELAY_SECONDS
)
from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead
from app.modules.signal_outreach.models.linkedin_activity import LinkedInActivity
from app.modules.signal_outreach.services.unipile_service import unipile_service
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
# HELPER FUNCTIONS
# ============================================

async def get_daily_counts(db: AsyncSession) -> dict:
    """Get today's connection and DM counts."""
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
    
    return {
        "connections_today": connections_today,
        "dms_today": dms_today
    }


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
    
    Flow:
    1. Check if lead exists
    2. Get provider_id if not already stored
    3. Check connection status
    4. If connected, send DM
    5. If not connected, return error (use send-connection first)
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
    
    # Get lead from database
    result = await db.execute(select(LinkedInLead).where(LinkedInLead.id == lead_id))
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get or fetch provider_id
    provider_id = lead.provider_id
    if not provider_id:
        profile_result = await unipile_service.get_profile(lead.linkedin_url)
        if not profile_result.get("success"):
            return SendDMResponse(
                success=False,
                message="Failed to get provider ID",
                lead_id=lead_id,
                error=profile_result.get("error")
            )
        provider_id = profile_result.get("provider_id")
        connection_status = profile_result.get("connection_status")
        
        # Update lead with provider info
        lead.provider_id = provider_id
        lead.connection_status = connection_status
        await db.commit()
    
    # Check connection status
    if lead.connection_status != "connected":
        return SendDMResponse(
            success=False,
            message="Not connected - send connection request first",
            lead_id=lead_id,
            dm_status="not_sent",
            error="Cannot send DM to non-connection. Use /send-connection first."
        )
    
    # Prepare message
    dm_message = request.message if request and request.message else lead.linkedin_dm
    if not dm_message:
        return SendDMResponse(
            success=False,
            message="No message provided",
            lead_id=lead_id,
            error="No custom message provided and no AI-generated DM available"
        )
    
    # Send DM
    send_result = await unipile_service.create_chat_and_send_dm(provider_id, dm_message)
    
    if send_result.get("success"):
        # Update lead
        lead.is_dm_sent = True
        lead.dm_sent_at = datetime.utcnow()
        lead.dm_status = "sent"
        await db.commit()
        
        # Create activity
        await create_activity(
            db=db,
            lead_id=lead_id,
            activity_type="dm_sent",
            message=dm_message[:200] if dm_message else None,
            lead_name=lead.full_name,
            lead_linkedin_url=lead.linkedin_url
        )
        
        logger.info(f"✅ DM sent to lead {lead_id}: {lead.full_name}")
        
        return SendDMResponse(
            success=True,
            message="DM sent successfully",
            lead_id=lead_id,
            dm_status="sent",
            sent_at=send_result.get("sent_at")
        )
    else:
        return SendDMResponse(
            success=False,
            message="Failed to send DM",
            lead_id=lead_id,
            error=send_result.get("error")
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
    
    Flow:
    1. Check if lead exists
    2. Get provider_id if not already stored
    3. Check connection status
    4. If already connected or pending, return appropriate message
    5. Send connection request
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
    
    # Get lead from database
    result = await db.execute(select(LinkedInLead).where(LinkedInLead.id == lead_id))
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get or fetch provider_id
    provider_id = lead.provider_id
    if not provider_id:
        profile_result = await unipile_service.get_profile(lead.linkedin_url)
        if not profile_result.get("success"):
            return SendConnectionResponse(
                success=False,
                message="Failed to get provider ID",
                lead_id=lead_id,
                error=profile_result.get("error")
            )
        provider_id = profile_result.get("provider_id")
        connection_status = profile_result.get("connection_status")
        
        # Update lead with provider info
        lead.provider_id = provider_id
        lead.connection_status = connection_status
        await db.commit()
    
    # Check if already connected
    if lead.connection_status == "connected":
        return SendConnectionResponse(
            success=True,
            message="Already connected - you can send a DM",
            lead_id=lead_id,
            connection_status="connected"
        )
    
    # Check if already pending
    if lead.connection_status == "pending":
        return SendConnectionResponse(
            success=False,
            message="Connection request already pending",
            lead_id=lead_id,
            connection_status="pending"
        )
    
    # Send connection request
    connection_message = request.message if request and request.message else None
    send_result = await unipile_service.send_connection_request(provider_id, connection_message)
    
    if send_result.get("success"):
        # Update lead
        lead.connection_status = "pending"
        lead.connection_sent_at = datetime.utcnow()
        await db.commit()
        
        # Create activity
        await create_activity(
            db=db,
            lead_id=lead_id,
            activity_type="connection_sent",
            message=connection_message,
            lead_name=lead.full_name,
            lead_linkedin_url=lead.linkedin_url,
            extra_data={"invitation_id": send_result.get("invitation_id")}
        )
        
        logger.info(f"✅ Connection request sent to lead {lead_id}: {lead.full_name}")
        
        return SendConnectionResponse(
            success=True,
            message="Connection request sent",
            lead_id=lead_id,
            connection_status="pending",
            invitation_id=send_result.get("invitation_id"),
            sent_at=send_result.get("sent_at")
        )
    else:
        # Handle already connected/invited errors
        if send_result.get("already_connected"):
            lead.connection_status = "connected"
            await db.commit()
            return SendConnectionResponse(
                success=True,
                message="Already connected",
                lead_id=lead_id,
                connection_status="connected"
            )
        elif send_result.get("already_invited"):
            lead.connection_status = "pending"
            await db.commit()
            return SendConnectionResponse(
                success=False,
                message="Already invited recently",
                lead_id=lead_id,
                connection_status="pending"
            )
        
        return SendConnectionResponse(
            success=False,
            message="Failed to send connection request",
            lead_id=lead_id,
            error=send_result.get("error")
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
    """
    try:
        data = await request.json()
        event_type = data.get("event")
        
        logger.info(f"📬 Webhook received: {event_type}")
        
        if event_type == "message_received":
            # Find lead by attendee_provider_id
            attendees = data.get("attendees", [])
            for attendee in attendees:
                if attendee.get("is_self") == 0:
                    provider_id = attendee.get("attendee_provider_id")
                    
                    result = await db.execute(
                        select(LinkedInLead).where(LinkedInLead.provider_id == provider_id)
                    )
                    lead = result.scalar_one_or_none()
                    
                    if lead:
                        lead.dm_status = "replied"
                        lead.last_reply_at = datetime.utcnow()
                        lead.next_follow_up_at = None  # Cancel follow-ups
                        await db.commit()
                        
                        # Create activity
                        await create_activity(
                            db=db,
                            lead_id=lead.id,
                            activity_type="dm_replied",
                            message=data.get("message", {}).get("text", ""),
                            lead_name=lead.full_name,
                            lead_linkedin_url=lead.linkedin_url
                        )
                        
                        logger.info(f"✅ Lead {lead.id} marked as replied")
        
        elif event_type == "new_relation":
            # Connection accepted
            provider_id = data.get("user_provider_id")
            
            if provider_id:
                result = await db.execute(
                    select(LinkedInLead).where(LinkedInLead.provider_id == provider_id)
                )
                lead = result.scalar_one_or_none()
                
                if lead:
                    lead.connection_status = "connected"
                    await db.commit()
                    
                    # Create activity
                    await create_activity(
                        db=db,
                        lead_id=lead.id,
                        activity_type="connection_accepted",
                        lead_name=lead.full_name,
                        lead_linkedin_url=lead.linkedin_url
                    )
                    
                    logger.info(f"✅ Lead {lead.id} connection accepted")
                    
                    # Auto-send DM if available
                    if lead.linkedin_dm and not lead.is_dm_sent:
                        dm_result = await unipile_service.create_chat_and_send_dm(
                            provider_id, lead.linkedin_dm
                        )
                        
                        if dm_result.get("success"):
                            lead.is_dm_sent = True
                            lead.dm_sent_at = datetime.utcnow()
                            lead.dm_status = "sent"
                            await db.commit()
                            
                            await create_activity(  
                                db=db, 
                                lead_id=lead.id,
                                activity_type="dm_sent",
                                message=lead.linkedin_dm[:200] if lead.linkedin_dm else None,
                                lead_name=lead.full_name,
                                lead_linkedin_url=lead.linkedin_url,
                                extra_data={"auto_sent": True}
                            )
                            
                            logger.info(f"✅ Auto-sent DM to lead {lead.id}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}
