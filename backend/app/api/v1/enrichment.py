import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.services.scraper_service import scraper_service
from app.services.intelligence_service import intelligence_service
from app.services.fate_service import generate_emails_for_lead 

router = APIRouter()

@router.post("/{lead_id}/enrich")
async def perform_enrichment(
    lead_id: int, 
    force_scrape: bool = Query(False), # New Flag to force fresh data if needed
    db: AsyncSession = Depends(get_db)
):
    """
    Smart Enrichment Logic:
    1. Check if we already have scraped posts in DB.
    2. If YES (and not forcing update) -> Reuse data (Fast, Free).
    3. If NO -> Call Apify Scraper (Slower, Costs Credits).
    4. Run AI Analysis (Gemini).
    5. Save everything (including raw posts) to DB.
    6. Regenerate Email immediately.
    """
    # A. Fetch Lead
    # We select 'scraped_data' specifically to check for cache
    result = await db.execute(text("SELECT * FROM leads WHERE id = :id"), {"id": lead_id})
    lead = result.mappings().first()
    
    if not lead or not lead.get("linkedin_url"):
        raise HTTPException(status_code=400, detail="Lead not found or missing LinkedIn URL")

    # --- LOGIC START ---
    final_scraped_data = []
    
    # B. Check Cache: Do we have saved posts?
    # We verify it's a list and has items.
    existing_data = lead.get("scraped_data")
    
    if existing_data and isinstance(existing_data, list) and len(existing_data) > 0 and not force_scrape:
        print(f"⚡ CACHE HIT: Reusing {len(existing_data)} saved posts for {lead['first_name']}")
        final_scraped_data = existing_data
    
    else:
        # C. Cache Miss: Scrape Fresh Data
        print(f"🔄 CACHE MISS: Scraping fresh data for {lead['first_name']} (Force={force_scrape})")
        scrape_result = await scraper_service.scrape_posts(lead.linkedin_url)
        
        if not scrape_result.get("success"):
            # Log failure but keep old status if it was completed before
            await db.execute(text("UPDATE leads SET enrichment_status = 'failed' WHERE id = :id"), {"id": lead_id})
            await db.commit()
            raise HTTPException(status_code=500, detail=f"Scraping failed: {scrape_result.get('error')}")
        
        final_scraped_data = scrape_result.get("scraped_data", [])

    # D. Analyze (Phase 2)
    # Always run AI analysis to get a fresh hook/style
    ai_analysis = await intelligence_service.analyze_profile(final_scraped_data)

    # E. Save Results (Phase 3)
    await db.execute(
        text("""
            UPDATE leads 
            SET 
                enrichment_status = 'completed',
                hiring_signal = :hiring,
                ai_variables = :ai_vars,
                scraped_data = :scraped_json,  -- Save the raw posts for next time
                personalized_intro = :intro,
                updated_at = NOW()
            WHERE id = :id
        """),
        {
            "id": lead_id,
            "hiring": ai_analysis.get("hiring_signal", False),
            "ai_vars": json.dumps(ai_analysis), 
            "scraped_json": json.dumps(final_scraped_data), # Store raw posts
            "intro": ai_analysis.get("summary_hook", "")
        }
    )
    await db.commit()

    # F. Regenerate Email (Phase 4)
    # Forces FATE service to inject the new hook immediately
    await generate_emails_for_lead(lead_id)

    return {
        "message": "Enrichment Complete", 
        "cached": bool(existing_data and not force_scrape), 
        "data": ai_analysis
    } 