from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession 
from app.db.session import get_db
from app.services.fate_service import generate_emails_for_lead
from app.services.instantly_service import send_lead_to_instantly # <--- NEW V2 SERVICE
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter()

# --- REQUEST MODEL (For Single Email / Small Button) ---
class SendEmailRequest(BaseModel):
    template_id: int
    email_body: str

# --- NEW REQUEST MODEL (For Sequence / Purple Button) ---
class SendSequenceRequest(BaseModel):
    email_1: str
    email_2: str
    email_3: str

# --- 1. GET ALL LEADS (Left Sidebar API) ---
@router.get("/")
async def get_leads(
    sector: Optional[str] = None,
    status: str = "valid",
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch verified leads for the campaign list.
    Supports filtering by Sector.
    """
    # Build Query Dynamically
    query_str = "SELECT id, first_name, last_name, company_name, designation, sector, email FROM leads WHERE verification_status = :status"
    params = {"status": status, "limit": limit, "offset": skip}

    if sector:
        query_str += " AND LOWER(sector) = LOWER(:sector)"
        params["sector"] = sector

    query_str += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query_str), params)
    leads = result.mappings().all() # Return as list of dicts
    
    return leads

# --- 2. GET SINGLE LEAD + EMAILS (Right Partition API) ---
@router.get("/{lead_id}")
async def get_lead_details(lead_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetches lead profile. 
    IF emails are missing, it triggers generation on the fly (Lazy Loading).
    """
    # 1. Fetch Lead
    query = text("SELECT * FROM leads WHERE id = :id")
    result = await db.execute(query, {"id": lead_id})
    lead = result.mappings().first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # 2. Check if emails exist. If not, Generate them now!
    if not lead.get("email_1_body"):
        # Trigger the Generator Service
        gen_result = await generate_emails_for_lead(lead_id)
        
        if "error" in gen_result:
            # If we can't generate (missing knowledge base), return lead without emails but with warning
            return {**dict(lead), "email_generation_error": gen_result["error"]}
        
        # Refetch lead to get the new emails
        result = await db.execute(query, {"id": lead_id})
        lead = result.mappings().first()

    return lead

# --- 3. SEND SINGLE EMAIL (Small Button) ---
@router.post("/{lead_id}/send")
async def send_email_to_provider(
    lead_id: int, 
    request: SendEmailRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Pushes the lead + ONE specific message to Instantly.ai
    """
    # 1. Fetch Lead Data
    query = text("SELECT * FROM leads WHERE id = :id")
    result = await db.execute(query, {"id": lead_id})
    lead = result.mappings().first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # 2. Convert to dict
    lead_data = dict(lead)

    # 3. Call Instantly Service (V2)
    result = send_lead_to_instantly(lead_data, request.email_body)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # 4. Mark as Sent
    await db.execute(
        text("UPDATE leads SET is_sent = TRUE, sent_at = NOW() WHERE id = :id"),
        {"id": lead_id}
    )
    await db.commit()

    return {"message": "Lead pushed to Instantly V2", "details": result}


# --- 4. SEND SEQUENCE (Purple Button - NEW) ---
@router.post("/{lead_id}/push-sequence")
async def push_sequence_to_instantly(
    lead_id: int, 
    request: SendSequenceRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Pushes Lead + ALL 3 Emails to Instantly.ai at once.
    """
    # 1. Fetch Lead Data
    query = text("SELECT * FROM leads WHERE id = :id")
    result = await db.execute(query, {"id": lead_id})
    lead = result.mappings().first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = dict(lead)

    # 2. Prepare Dictionary Payload for Service
    # This triggers the "dict" logic in your instantly_service.py
    emails_payload = {
        "email_1": request.email_1,
        "email_2": request.email_2,
        "email_3": request.email_3 
    }

    # 3. Call Service
    result = send_lead_to_instantly(lead_data, emails_payload)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # 4. Update DB status
    await db.execute(
        text("UPDATE leads SET is_sent = TRUE, sent_at = NOW() WHERE id = :id"),
        {"id": lead_id}
    )
    await db.commit()

    return {"message": "Sequence pushed successfully", "details": result} 