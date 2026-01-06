from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession 
from app.db.session import get_db
from app.services.fate_service import generate_emails_for_lead
from app.services.instantly_service import send_lead_to_instantly  
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.models.email import SendEmailRequest, SendSequenceRequest  

router = APIRouter()

# --- 1. GET CAMPAIGN LEADS (All Verified Leads) ---
@router.get("/")
async def get_campaign_leads(
    sector: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch ALL verified leads (verification_status = 'valid').
    Also returns count of leads with missing data for frontend alert.
    """
    # Main query - get all verified leads
    query_str = """
        SELECT 
            id, first_name, last_name, company_name, designation, sector, email, 
            verification_status, lead_stage,
            hiring_signal, enrichment_status, ai_variables
        FROM leads 
        WHERE verification_status = 'valid'
    """
    params = {"limit": limit, "offset": skip}

    if sector:
        query_str += " AND LOWER(sector) = LOWER(:sector)"
        params["sector"] = sector

    query_str += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query_str), params)
    leads = result.mappings().all() 
    
    # Count leads with missing data (for frontend alert)
    count_query = """
        SELECT COUNT(*) as incomplete_count
        FROM leads 
        WHERE verification_status = 'valid'
        AND (company_name IS NULL OR linkedin_url IS NULL OR mobile_number IS NULL 
             OR designation IS NULL OR sector IS NULL)
    """
    count_result = await db.execute(text(count_query))
    incomplete_count = count_result.scalar() or 0
    
    return {
        "leads": list(leads),
        "incomplete_leads_count": incomplete_count
    } 

# --- 2. GET ENRICHMENT LEADS (Leads with Missing Data) --- 
@router.get("/enrichment")
async def get_enrichment_leads(
    sector: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch leads that have valid email but are missing some data.
    These have valid emails but missing Mobile/LinkedIn/Company/Designation/Sector.
    """
    # Filter by verified status AND any missing field
    query_str = """
        SELECT id, first_name, last_name, company_name, designation, sector, email, mobile_number, linkedin_url, lead_stage 
        FROM leads 
        WHERE verification_status = 'valid'
        AND (company_name IS NULL OR linkedin_url IS NULL OR mobile_number IS NULL 
             OR designation IS NULL OR sector IS NULL)
    """
    params = {"limit": limit, "offset": skip}

    if sector:
        query_str += " AND LOWER(sector) = LOWER(:sector)"
        params["sector"] = sector

    query_str += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query_str), params)
    leads = result.mappings().all() 
    
    return leads

# --- 3. GET SINGLE LEAD DETAILS (Right Partition) ---
@router.get("/{lead_id}")
async def get_lead_details(lead_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetches lead profile (Works for both Campaign and Enrichment leads).
    Triggers lazy email generation if needed.
    """
    # 1. Fetch Lead
    # SELECT * automatically grabs the new 'personalized_intro', 'hiring_signal', etc.
    query = text("SELECT * FROM leads WHERE id = :id")
    result = await db.execute(query, {"id": lead_id})
    lead = result.mappings().first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # 2. Lazy Load Emails (Only if it's a Campaign lead or we force it)
    if not lead.get("email_1_body"):
        gen_result = await generate_emails_for_lead(lead_id)
        
        if "error" in gen_result:
            return {**dict(lead), "email_generation_error": gen_result["error"]}
        
        # Refetch to get the newly generated body
        result = await db.execute(query, {"id": lead_id})
        lead = result.mappings().first()

    return lead

# --- 4. SEND SINGLE EMAIL (Small Button) ---
@router.post("/{lead_id}/send") 
async def send_email_to_provider(
    lead_id: int, 
    request: SendEmailRequest, 
    db: AsyncSession = Depends(get_db)
):
    query = text("SELECT * FROM leads WHERE id = :id")
    result = await db.execute(query, {"id": lead_id})
    lead = result.mappings().first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = dict(lead)
    result = send_lead_to_instantly(lead_data, request.email_body)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    await db.execute(
        text("UPDATE leads SET is_sent = TRUE, sent_at = NOW() WHERE id = :id"),
        {"id": lead_id}
    )
    await db.commit()

    return {"message": "Lead pushed to Instantly V2", "details": result}

# --- 5. SEND SEQUENCE (Purple Button) ---
@router.post("/{lead_id}/push-sequence")
async def push_sequence_to_instantly(
    lead_id: int, 
    request: SendSequenceRequest, 
    db: AsyncSession = Depends(get_db)
):
    query = text("SELECT * FROM leads WHERE id = :id")
    result = await db.execute(query, {"id": lead_id})
    lead = result.mappings().first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = dict(lead)
    emails_payload = {
        "email_1": request.email_1,
        "email_2": request.email_2,
        "email_3": request.email_3,
        "email_1_subject": request.email_1_subject,
        "email_2_subject": request.email_2_subject,
        "email_3_subject": request.email_3_subject 
    }

    result = send_lead_to_instantly(lead_data, emails_payload)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    await db.execute(
        text("UPDATE leads SET is_sent = TRUE, sent_at = NOW() WHERE id = :id"),
        {"id": lead_id}
    )
    await db.commit()

    return {"message": "Sequence pushed successfully", "details": result}


# ============================================
# BULK OPERATIONS (NEW)
# ============================================
from app.services.instantly_service import send_leads_bulk_to_instantly

# Request model for bulk operations
class BulkLeadRequest(BaseModel):
    lead_ids: List[int]


# --- 6. BULK ELIGIBILITY CHECK (Pre-flight) ---
@router.post("/bulk-check")
async def check_bulk_eligibility(
    request: BulkLeadRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Pre-flight check before bulk push.
    Categorizes leads into:
    - ready: Can be pushed (enriched OR no LinkedIn)
    - needs_enrichment: Has LinkedIn but not enriched yet
    - invalid_email: Missing email address
    - already_sent: Already pushed to Instantly (is_sent = true)
    """
    if not request.lead_ids:
        return {"error": "No lead IDs provided"}
    
    if len(request.lead_ids) > 100:
        return {"error": "Maximum 100 leads allowed per batch"}

    # Fetch all selected leads
    placeholders = ",".join([f":id_{i}" for i in range(len(request.lead_ids))])
    params = {f"id_{i}": lid for i, lid in enumerate(request.lead_ids)}
    
    query = text(f"""
        SELECT id, email, linkedin_url, enrichment_status, ai_variables, is_sent
        FROM leads 
        WHERE id IN ({placeholders})
    """)
    
    result = await db.execute(query, params)
    leads = result.mappings().all()
    
    # Categorize leads
    ready = []
    needs_enrichment = []
    invalid_email = []
    already_sent = []
    
    for lead in leads:
        lead_id = lead["id"]
        
        # Check if already sent
        if lead.get("is_sent"):
            already_sent.append(lead_id)
            continue
        
        # Check for valid email
        if not lead.get("email"):
            invalid_email.append(lead_id)
            continue
        
        # Check enrichment requirement
        has_linkedin = bool(lead.get("linkedin_url"))
        is_enriched = lead.get("enrichment_status") == "completed" or lead.get("ai_variables") is not None
        
        if has_linkedin and not is_enriched:
            # Has LinkedIn but NOT enriched -> Block
            needs_enrichment.append(lead_id)
        else:
            # Either: No LinkedIn (use generic) OR LinkedIn + Enriched (use AI)
            ready.append(lead_id)
    
    return {
        "total": len(request.lead_ids),
        "ready": len(ready),
        "needs_enrichment": len(needs_enrichment),
        "invalid_email": len(invalid_email),
        "already_sent": len(already_sent),
        "details": {
            "ready": ready,
            "needs_enrichment": needs_enrichment,
            "invalid_email": invalid_email,
            "already_sent": already_sent
        }
    }


# --- 7. BULK PUSH TO INSTANTLY ---
@router.post("/bulk-push")
async def bulk_push_to_instantly(
    request: BulkLeadRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Push multiple leads to Instantly in a single API call.
    Only pushes leads that are:
    - Not already sent (is_sent = false)
    - Have valid email
    - Either: No LinkedIn (generic email OK) OR LinkedIn + Enriched (AI email)
    
    Leads with LinkedIn but NOT enriched are SKIPPED (not blocked entirely).
    """
    if not request.lead_ids:
        raise HTTPException(status_code=400, detail="No lead IDs provided")
    
    if len(request.lead_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 leads allowed per batch")

    # Fetch all selected leads with full data needed for Instantly
    placeholders = ",".join([f":id_{i}" for i in range(len(request.lead_ids))])
    params = {f"id_{i}": lid for i, lid in enumerate(request.lead_ids)}
    
    query = text(f"""
        SELECT 
            id, email, first_name, last_name, company_name, designation, sector,
            linkedin_url, personalized_intro,
            email_1_subject, email_1_body,
            email_2_subject, email_2_body,
            email_3_subject, email_3_body,
            enrichment_status, ai_variables, is_sent
        FROM leads 
        WHERE id IN ({placeholders})
    """)
    
    result = await db.execute(query, params)
    leads = result.mappings().all()
    
    # Filter and prepare leads for Instantly
    leads_to_push = []
    skipped_needs_enrichment = []
    skipped_no_email = []
    skipped_already_sent = []
    
    for lead in leads:
        lead_dict = dict(lead)
        lead_id = lead_dict["id"]
        
        # Skip if already sent
        if lead_dict.get("is_sent"):
            skipped_already_sent.append(lead_id)
            continue
        
        # Skip if no email
        if not lead_dict.get("email"):
            skipped_no_email.append(lead_id)
            continue
        
        # Check enrichment requirement
        has_linkedin = bool(lead_dict.get("linkedin_url"))
        is_enriched = lead_dict.get("enrichment_status") == "completed" or lead_dict.get("ai_variables") is not None
        
        if has_linkedin and not is_enriched:
            # Has LinkedIn but NOT enriched -> Skip this lead
            skipped_needs_enrichment.append(lead_id)
            continue
        
        # This lead is eligible - add to push list
        leads_to_push.append(lead_dict)
    
    if not leads_to_push:
        return {
            "success": False,
            "message": "No eligible leads to push",
            "skipped_needs_enrichment": skipped_needs_enrichment,
            "skipped_no_email": skipped_no_email,
            "skipped_already_sent": skipped_already_sent
        }
    
    # --- AUTO-GENERATE EMAILS FOR LEADS WITHOUT THEM ---
    # Find leads that don't have email_1_body (never had lazy load triggered)
    leads_needing_emails = [lead for lead in leads_to_push if not lead.get("email_1_body")]
    
    if leads_needing_emails:
        import logging
        logger = logging.getLogger("bulk_push")
        logger.info(f"📧 Auto-generating emails for {len(leads_needing_emails)} leads...")
        
        for lead in leads_needing_emails:
            try:
                await generate_emails_for_lead(lead["id"])
            except Exception as e:
                logger.warning(f"⚠️ Failed to generate emails for lead {lead['id']}: {e}")
        
        # Refetch the leads that had emails generated to get updated data
        refetch_ids = [lead["id"] for lead in leads_needing_emails]
        refetch_placeholders = ",".join([f":rid_{i}" for i in range(len(refetch_ids))])
        refetch_params = {f"rid_{i}": lid for i, lid in enumerate(refetch_ids)}
        
        refetch_query = text(f"""
            SELECT 
                id, email, first_name, last_name, company_name, designation, sector,
                linkedin_url, personalized_intro,
                email_1_subject, email_1_body,
                email_2_subject, email_2_body,
                email_3_subject, email_3_body,
                enrichment_status, ai_variables, is_sent
            FROM leads 
            WHERE id IN ({refetch_placeholders}) 
        """)
        
        refetch_result = await db.execute(refetch_query, refetch_params)
        refetched_leads = {lead["id"]: dict(lead) for lead in refetch_result.mappings().all()}
        
        # Update the leads_to_push with refreshed data
        leads_to_push = [
            refetched_leads.get(lead["id"], lead) if lead["id"] in refetched_leads else lead
            for lead in leads_to_push
        ]
        
        logger.info(f"✅ Email generation complete for {len(leads_needing_emails)} leads")
    
    # Call bulk Instantly service
    instantly_result = send_leads_bulk_to_instantly(leads_to_push)
    
    if "error" in instantly_result:
        raise HTTPException(status_code=500, detail=instantly_result["error"])
    
    # Update is_sent for successfully pushed leads
    pushed_lead_ids = [lead["id"] for lead in leads_to_push]
    
    if pushed_lead_ids:
        update_placeholders = ",".join([f":uid_{i}" for i in range(len(pushed_lead_ids))])
        update_params = {f"uid_{i}": lid for i, lid in enumerate(pushed_lead_ids)}
        
        await db.execute(
            text(f"UPDATE leads SET is_sent = TRUE, sent_at = NOW() WHERE id IN ({update_placeholders})"),
            update_params
        )
        await db.commit()
    
    return {
        "success": True,
        "message": f"Successfully pushed {instantly_result.get('leads_uploaded', 0)} leads to Instantly",
        "total_selected": len(request.lead_ids),
        "total_pushed": len(leads_to_push),
        "leads_uploaded": instantly_result.get("leads_uploaded", 0),
        "duplicated_in_instantly": instantly_result.get("duplicated_leads", 0),
        "skipped_needs_enrichment": skipped_needs_enrichment,
        "skipped_no_email": skipped_no_email,
        "skipped_already_sent": skipped_already_sent,
        "instantly_response": instantly_result
    } 