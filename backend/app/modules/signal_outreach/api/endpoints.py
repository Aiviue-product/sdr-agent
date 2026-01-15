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
from app.modules.signal_outreach.services.linkedin_outreach_service import LinkedInOutreachService
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
    Logic is orchestrated by LinkedInOutreachService.
    """
    logger.info(f"🔍 LinkedIn search requested: {request.keywords}")
    
    try:
        service = LinkedInOutreachService(db)
        result = await service.run_full_outreach_search(
            keywords=request.keywords,
            date_filter=request.date_filter,
            posts_per_keyword=request.posts_per_keyword
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500, 
                detail=result.get("error", "Search failed")
            )
        
        return LinkedInSearchResponse(
            success=True,
            message=result.get("message", "Search processed"),
            stats=result.get("stats", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ LinkedIn search endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
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
    """
    logger.info(f"🔄 Refreshing analysis for lead {lead_id}")
    
    try:
        service = LinkedInOutreachService(db)
        result = await service.refresh_lead_analysis(lead_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404 if "not found" in result.get("error", "").lower() else 400, 
                                detail=result.get("error"))
        
        ai_result = result["ai_result"]
        lead = result["lead"]
        
        return {
            "success": True,
            "message": f"Analysis refreshed for {lead.get('full_name')}",
            "lead_id": lead_id,
            "hiring_signal": ai_result.get("hiring_signal", False),
            "hiring_roles": ai_result.get("hiring_roles", ""),
            "linkedin_dm": ai_result.get("linkedin_dm", "")[:100] + "..." if len(ai_result.get("linkedin_dm", "")) > 100 else ai_result.get("linkedin_dm", "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh failed for lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    """
    lead_ids = request.lead_ids
    
    if not lead_ids:
        raise HTTPException(status_code=400, detail="No lead IDs provided")
    
    logger.info(f"🔄 Bulk refreshing {len(lead_ids)} leads")
    
    try:
        service = LinkedInOutreachService(db)
        results = await service.bulk_refresh_leads(lead_ids)
        
        logger.info(f"✅ Bulk refresh complete: {results['success_count']} success, {results['failed_count']} failed")
        
        return {
            "success": True,
            "message": f"Refreshed {results['success_count']} leads, {results['failed_count']} failed",
            **results
        }
    except Exception as e:
        logger.error(f"Bulk refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

