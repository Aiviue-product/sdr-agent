from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession 
from app.db.session import get_db
from app.services.fate_service import generate_emails_for_lead
from typing import Optional, List

router = APIRouter()

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

# --- 3. SEND EMAIL (Placeholder for Phase 3) ---
@router.post("/{lead_id}/send")
async def send_email_placeholder(lead_id: int, template_id: int = 1):
    """
    Placeholder for Instantly.ai / Cron Job logic.
    """
    return {
        "message": f"Email {template_id} queued for Lead {lead_id}", 
        "mode": "Simulated (Phase 3 Impl)",
        "status": "queued"
    }