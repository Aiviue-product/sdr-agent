from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession 
from app.db.session import get_db
from app.services.fate_service import generate_emails_for_lead
from app.services.instantly_service import send_lead_to_instantly  
from typing import Optional, List
from pydantic import BaseModel
from app.models.email import SendEmailRequest, SendSequenceRequest 

router = APIRouter()



# --- 1. GET CAMPAIGN LEADS (Main List - Campaign Ready) ---
@router.get("/")
async def get_campaign_leads(
    sector: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch ONLY fully populated leads (lead_stage = 'campaign').
    These are the ones ready for outreach.
    """
    # Filter by lead_stage = 'campaign'
    query_str = """
        SELECT id, first_name, last_name, company_name, designation, sector, email, verification_status, lead_stage 
        FROM leads 
        WHERE lead_stage = 'campaign'
    """
    params = {"limit": limit, "offset": skip}

    if sector:
        query_str += " AND LOWER(sector) = LOWER(:sector)"
        params["sector"] = sector

    query_str += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query_str), params)
    leads = result.mappings().all() 
    
    return leads

# --- 2. GET ENRICHMENT LEADS (New Page - Missing Data) ---
@router.get("/enrichment")
async def get_enrichment_leads(
    sector: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch ONLY leads that need more info (lead_stage = 'enrichment').
    These have valid emails but missing Mobile/LinkedIn/Company.
    """
    # Filter by lead_stage = 'enrichment'
    query_str = """
        SELECT id, first_name, last_name, company_name, designation, sector, email, mobile_number, linkedin_url, lead_stage 
        FROM leads 
        WHERE lead_stage = 'enrichment'
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
    query = text("SELECT * FROM leads WHERE id = :id")
    result = await db.execute(query, {"id": lead_id})
    lead = result.mappings().first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # 2. Lazy Load Emails (Only if it's a Campaign lead or we force it)
    # Usually we only generate emails for campaign-ready leads, but we can allow it for all.
    if not lead.get("email_1_body"):
        gen_result = await generate_emails_for_lead(lead_id)
        
        if "error" in gen_result:
            return {**dict(lead), "email_generation_error": gen_result["error"]}
        
        # Refetch
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
        "email_3": request.email_3 
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