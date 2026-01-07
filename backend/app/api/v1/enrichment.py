from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.repositories.lead_repository import LeadRepository
from app.services.scraper_service import scraper_service
from app.services.intelligence_service import intelligence_service
from app.services.fate_service import generate_emails_for_lead 

router = APIRouter()

@router.post("/{lead_id}/enrich")
async def perform_enrichment(
    lead_id: int, 
    force_scrape: bool = Query(False), # Flag to force fresh data if needed
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
    # Initialize repository
    lead_repo = LeadRepository(db)
    
    # A. Fetch Lead (via repository)
    lead = await lead_repo.get_by_id(lead_id)
    
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
            # Log failure (via repository)
            await lead_repo.update_enrichment_failed(lead_id)
            raise HTTPException(status_code=500, detail=f"Scraping failed: {scrape_result.get('error')}")
        
        final_scraped_data = scrape_result.get("scraped_data", [])

    # D. Analyze (Phase 2)
    # Always run AI analysis to get a fresh hook/style
    ai_analysis = await intelligence_service.analyze_profile(final_scraped_data)

    # E. Save Results (Phase 3) - via repository
    await lead_repo.update_enrichment_completed(lead_id, ai_analysis, final_scraped_data)

    # F. Regenerate Email (Phase 4)
    # Forces FATE service to inject the new hook immediately
    await generate_emails_for_lead(lead_id)

    return {
        "message": "Enrichment Complete", 
        "cached": bool(existing_data and not force_scrape), 
        "data": ai_analysis
    } 