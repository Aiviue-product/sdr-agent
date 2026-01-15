"""
LinkedIn Signal Outreach API Endpoints
Handles searching LinkedIn, analyzing posts, and managing leads.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.db.session import get_db
from app.modules.signal_outreach.repositories.linkedin_lead_repository import LinkedInLeadRepository
from app.modules.signal_outreach.services.linkedin_search_service import linkedin_search_service
from app.modules.signal_outreach.services.linkedin_intelligence_service import linkedin_intelligence_service
from app.modules.signal_outreach.api.schemas import (
    LinkedInSearchRequest,
    LinkedInSearchResponse,
    LinkedInLeadSummary,
    LinkedInLeadDetail,
    LinkedInLeadsListResponse,
    LinkedInKeywordsResponse
)

router = APIRouter()
logger = logging.getLogger("linkedin_api")


# ============================================
# SEARCH ENDPOINT
# ============================================

@router.post("/search", response_model=LinkedInSearchResponse)
async def search_linkedin_posts(
    request: LinkedInSearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Search LinkedIn posts by keywords and save discovered leads.
    
    Process:
    1. Call Apify to search posts by keywords
    2. Parse author data from posts
    3. Run AI analysis on each post (hiring signals, pain points)
    4. Generate personalized DM for each lead
    5. Save to database (hybrid upsert - append posts to existing leads)
    
    Returns immediately with search stats. AI analysis runs for each lead.
    """
    logger.info(f"🔍 LinkedIn search requested: {request.keywords}")
    
    try:
        # 1. Search LinkedIn via Apify
        search_result = await linkedin_search_service.search_by_keywords(
            keywords=request.keywords,
            date_filter=request.date_filter,
            posts_per_keyword=request.posts_per_keyword
        )
        
        if not search_result.get("success"):
            raise HTTPException(
                status_code=500, 
                detail=search_result.get("error", "Search failed")
            )
        
        leads = search_result.get("leads", [])
        
        if not leads:
            return LinkedInSearchResponse(
                success=True,
                message="No leads found for the given keywords",
                stats=search_result.get("stats", {})
            )
        
        # 2. Enrich each lead with AI analysis + DM
        enriched_leads = []
        for lead in leads:
            try:
                # Get post data for analysis
                post_data = lead.get("post_data", {})
                author_name = lead.get("full_name", "")
                author_headline = lead.get("headline", "")
                
                # Run AI analysis and generate DM
                ai_result = await linkedin_intelligence_service.analyze_and_generate_dm(
                    post_data=post_data,
                    author_name=author_name,
                    author_headline=author_headline
                )
                
                # Merge AI results into lead
                lead["hiring_signal"] = ai_result.get("hiring_signal", False)
                lead["hiring_roles"] = ai_result.get("hiring_roles", "")
                lead["pain_points"] = ai_result.get("pain_points", "")
                lead["ai_variables"] = ai_result.get("ai_variables", {})
                lead["linkedin_dm"] = ai_result.get("linkedin_dm", "")
                
                enriched_leads.append(lead)
                
            except Exception as e:
                logger.error(f"AI enrichment failed for {lead.get('full_name')}: {e}")
                # Keep lead with default values
                enriched_leads.append(lead)
        
        # 3. Save to database
        repo = LinkedInLeadRepository(db)
        save_result = await repo.bulk_upsert_leads(enriched_leads)
        
        logger.info(f"✅ Search complete: {save_result}")
        
        return LinkedInSearchResponse(
            success=True,
            message=f"Found {len(leads)} leads. Inserted: {save_result['inserted_count']}, Updated: {save_result['updated_count']}, Skipped: {save_result['skipped_count']}",
            stats={
                **search_result.get("stats", {}),
                "inserted_count": save_result["inserted_count"],
                "updated_count": save_result["updated_count"],
                "skipped_count": save_result["skipped_count"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ LinkedIn search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LEADS LIST ENDPOINT
# ============================================

@router.get("/leads")
async def get_linkedin_leads(
    keyword: Optional[str] = Query(default=None, description="Filter by search keyword"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all LinkedIn leads with optional keyword filter.
    Supports pagination.
    
    Returns cumulative view - all leads from all searches.
    """
    repo = LinkedInLeadRepository(db)
    
    # Get leads
    leads = await repo.get_all_leads(keyword=keyword, skip=skip, limit=limit)
    
    # Get total count for pagination
    total_count = await repo.get_total_count(keyword=keyword)
    
    # Get unique keywords for filter dropdown
    unique_keywords = await repo.get_unique_keywords()
    
    # Convert to response format
    leads_list = []
    for lead in leads:
        leads_list.append({
            "id": lead["id"],
            "full_name": lead["full_name"],
            "first_name": lead.get("first_name"),
            "last_name": lead.get("last_name"),
            "company_name": lead.get("company_name"),
            "is_company": lead.get("is_company", False),
            "linkedin_url": lead["linkedin_url"],
            "headline": lead.get("headline"),
            "search_keyword": lead.get("search_keyword"),
            "hiring_signal": lead.get("hiring_signal", False),
            "hiring_roles": lead.get("hiring_roles"),
            "is_dm_sent": lead.get("is_dm_sent", False),
            "created_at": str(lead["created_at"]) if lead.get("created_at") else None
        })
    
    return {
        "leads": leads_list,
        "total_count": total_count,
        "skip": skip,
        "limit": limit,
        "available_keywords": unique_keywords
    }


# ============================================
# LEAD DETAIL ENDPOINT
# ============================================

@router.get("/leads/{lead_id}")
async def get_linkedin_lead_detail(
    lead_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get full details of a single LinkedIn lead.
    Includes AI analysis, post data, and personalized DM.
    """
    repo = LinkedInLeadRepository(db)
    lead = await repo.get_by_id(lead_id)
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Parse post_data if it's a string
    post_data = lead.get("post_data")
    if isinstance(post_data, str):
        try:
            import json
            post_data = json.loads(post_data)
        except:
            post_data = []
    
    # Parse ai_variables if it's a string
    ai_variables = lead.get("ai_variables")
    if isinstance(ai_variables, str):
        try:
            import json
            ai_variables = json.loads(ai_variables)
        except:
            ai_variables = {}
    
    return {
        "id": lead["id"],
        "full_name": lead["full_name"],
        "first_name": lead.get("first_name"),
        "last_name": lead.get("last_name"),
        "company_name": lead.get("company_name"),
        "is_company": lead.get("is_company", False),
        "linkedin_url": lead["linkedin_url"],
        "headline": lead.get("headline"),
        "profile_image_url": lead.get("profile_image_url"),
        "search_keyword": lead.get("search_keyword"),
        "post_data": post_data,
        "hiring_signal": lead.get("hiring_signal", False),
        "hiring_roles": lead.get("hiring_roles"),
        "pain_points": lead.get("pain_points"),
        "ai_variables": ai_variables,
        "linkedin_dm": lead.get("linkedin_dm"),
        "is_dm_sent": lead.get("is_dm_sent", False),
        "dm_sent_at": str(lead["dm_sent_at"]) if lead.get("dm_sent_at") else None,
        "created_at": str(lead["created_at"]) if lead.get("created_at") else None,
        "updated_at": str(lead["updated_at"]) if lead.get("updated_at") else None
    }


# ============================================
# UTILITY ENDPOINTS
# ============================================

@router.get("/keywords", response_model=LinkedInKeywordsResponse)
async def get_available_keywords(db: AsyncSession = Depends(get_db)):
    """
    Get list of unique search keywords for filter dropdown.
    """
    repo = LinkedInLeadRepository(db)
    keywords = await repo.get_unique_keywords()
    return LinkedInKeywordsResponse(keywords=keywords)


# ============================================
# REFRESH ANALYSIS ENDPOINTS
# ============================================

@router.post("/leads/{lead_id}/refresh")
async def refresh_single_lead_analysis(
    lead_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Re-run AI analysis on a single lead using existing post_data.
    
    USE CASE: When AI prompts are improved, refresh existing leads
    without re-scraping from LinkedIn (saves Apify credits).
    
    Process:
    1. Fetch lead from database (with existing post_data)
    2. Re-run AI analysis on the first post
    3. Update lead with new hiring_signal, hiring_roles, pain_points, linkedin_dm
    """
    logger.info(f"🔄 Refreshing analysis for lead {lead_id}")
    
    repo = LinkedInLeadRepository(db)
    
    # 1. Get existing lead
    lead = await repo.get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # 2. Parse post_data
    post_data = lead.get("post_data")
    if isinstance(post_data, str):
        try:
            import json
            post_data = json.loads(post_data)
        except:
            post_data = []
    
    if not post_data or len(post_data) == 0:
        raise HTTPException(
            status_code=400, 
            detail="No post data available for this lead. Cannot refresh analysis."
        )
    
    # 3. Run AI analysis on first post (most recent)
    first_post = post_data[0] if isinstance(post_data, list) else post_data
    
    try:
        ai_result = await linkedin_intelligence_service.analyze_and_generate_dm(
            post_data=first_post,
            author_name=lead.get("full_name", ""),
            author_headline=lead.get("headline", "")
        )
    except Exception as e:
        logger.error(f"AI analysis failed for lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")
    
    # 4. Update lead in database
    await repo.update_ai_enrichment(
        lead_id=lead_id,
        hiring_signal=ai_result.get("hiring_signal", False),
        hiring_roles=ai_result.get("hiring_roles", ""),
        pain_points=ai_result.get("pain_points", ""),
        ai_variables=ai_result.get("ai_variables", {}),
        linkedin_dm=ai_result.get("linkedin_dm", "")
    )
    
    logger.info(f"✅ Refresh complete for lead {lead_id}: hiring_signal={ai_result.get('hiring_signal')}")
    
    return {
        "success": True,
        "message": f"Analysis refreshed for {lead.get('full_name')}",
        "lead_id": lead_id,
        "hiring_signal": ai_result.get("hiring_signal", False),
        "hiring_roles": ai_result.get("hiring_roles", ""),
        "linkedin_dm": ai_result.get("linkedin_dm", "")[:100] + "..." if len(ai_result.get("linkedin_dm", "")) > 100 else ai_result.get("linkedin_dm", "")
    }


from pydantic import BaseModel
from typing import List

class BulkRefreshRequest(BaseModel):
    lead_ids: List[int]


@router.post("/leads/bulk-refresh")
async def refresh_bulk_leads_analysis(
    request: BulkRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Re-run AI analysis on multiple leads using existing post_data.
    
    USE CASE: Bulk refresh after AI prompt improvements.
    
    NOTE: On FREE tier (5 req/min), this will be slow (~13s per lead).
    On PAID tier, parallel processing is enabled.
    
    Process:
    1. Fetch all leads from database
    2. Re-run AI analysis on each (sequential on free, parallel on paid)
    3. Update all leads with new analysis
    """
    lead_ids = request.lead_ids
    
    if not lead_ids:
        raise HTTPException(status_code=400, detail="No lead IDs provided")
    
    if len(lead_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 leads per batch")
    
    logger.info(f"🔄 Bulk refreshing {len(lead_ids)} leads")
    
    repo = LinkedInLeadRepository(db)
    results = {
        "success_count": 0,
        "failed_count": 0,
        "errors": []
    }
    
    for lead_id in lead_ids:
        try:
            # Get lead
            lead = await repo.get_by_id(lead_id)
            if not lead:
                results["failed_count"] += 1
                results["errors"].append({"lead_id": lead_id, "error": "Not found"})
                continue
            
            # Parse post_data
            post_data = lead.get("post_data")
            if isinstance(post_data, str):
                import json
                post_data = json.loads(post_data)
            
            if not post_data or len(post_data) == 0:
                results["failed_count"] += 1
                results["errors"].append({"lead_id": lead_id, "error": "No post data"})
                continue
            
            # Run AI analysis
            first_post = post_data[0] if isinstance(post_data, list) else post_data
            
            ai_result = await linkedin_intelligence_service.analyze_and_generate_dm(
                post_data=first_post,
                author_name=lead.get("full_name", ""),
                author_headline=lead.get("headline", "")
            )
            
            # Update lead
            await repo.update_ai_enrichment(
                lead_id=lead_id,
                hiring_signal=ai_result.get("hiring_signal", False),
                hiring_roles=ai_result.get("hiring_roles", ""),
                pain_points=ai_result.get("pain_points", ""),
                ai_variables=ai_result.get("ai_variables", {}),
                linkedin_dm=ai_result.get("linkedin_dm", "")
            )
            
            results["success_count"] += 1
            logger.info(f"   ✅ Lead {lead_id}: hiring_signal={ai_result.get('hiring_signal')}")
            
        except Exception as e:
            results["failed_count"] += 1
            results["errors"].append({"lead_id": lead_id, "error": str(e)})
            logger.error(f"   ❌ Lead {lead_id} failed: {e}")
    
    logger.info(f"✅ Bulk refresh complete: {results['success_count']} success, {results['failed_count']} failed")
    
    return {
        "success": True,
        "message": f"Refreshed {results['success_count']} leads, {results['failed_count']} failed",
        **results
    }

