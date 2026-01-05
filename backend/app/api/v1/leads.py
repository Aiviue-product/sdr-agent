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