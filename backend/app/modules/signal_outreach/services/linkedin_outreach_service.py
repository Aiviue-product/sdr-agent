"""
LinkedIn Outreach Service (Orchestrator)
Orchestrates the flow between Search, Intelligence, and Repository.
"""
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.signal_outreach.services.linkedin_search_service import linkedin_search_service
from app.modules.signal_outreach.services.linkedin_intelligence_service import linkedin_intelligence_service
from app.modules.signal_outreach.repositories.linkedin_lead_repository import LinkedInLeadRepository
from app.shared.utils.json_utils import safe_json_parse

logger = logging.getLogger("linkedin_outreach_service")

class LinkedInOutreachService:
    """
    Orchestrates the LinkedIn lead lifecycle: Search -> AI Analysis -> Database Storage.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LinkedInLeadRepository(db)

    async def run_full_outreach_search(
        self, 
        keywords: List[str], 
        date_filter: str = "past-week", 
        posts_per_keyword: int = 10
    ) -> Dict[str, Any]:
        """
        Executes the full pipeline:
        1. Query Apify for LinkedIn posts
        2. Run Gemini AI analysis (hiring signals, roles, contact info)
        3. Persist leads to database with deduplication logic
        """
        logger.info(f"🚀 Starting full outreach search for keywords: {keywords}")

        # 1. Search LinkedIn via Apify
        search_result = await linkedin_search_service.search_by_keywords(
            keywords=keywords,
            date_filter=date_filter,
            posts_per_keyword=posts_per_keyword
        )
        
        if not search_result.get("success"):
            logger.error(f"❌ Search failed: {search_result.get('error')}")
            return search_result

        leads = search_result.get("leads", [])
        if not leads:
            return {
                "success": True, 
                "message": "No leads found for the given keywords", 
                "stats": search_result.get("stats", {})
            }

        # 2. Enrich each lead with AI analysis + DM
        enriched_leads = []
        for lead in leads:
            try:
                # Use Intelligence Service to analyze the post and generate DM
                ai_result = await linkedin_intelligence_service.analyze_and_generate_dm(
                    post_data=lead.get("post_data", {}),
                    author_name=lead.get("full_name", ""),
                    author_headline=lead.get("headline", "")
                )
                
                # Merge AI results into lead dictionary
                lead.update({
                    "hiring_signal": ai_result.get("hiring_signal", False),
                    "hiring_roles": ai_result.get("hiring_roles", ""),
                    "pain_points": ai_result.get("pain_points", ""),
                    "ai_variables": ai_result.get("ai_variables", {}),
                    "linkedin_dm": ai_result.get("linkedin_dm", "")
                })
                
                enriched_leads.append(lead)
                
            except Exception as e:
                logger.error(f"⚠️ AI enrichment failed for {lead.get('full_name')}: {e}")
                # Keep lead with default values to prevent data loss
                enriched_leads.append(lead)
        
        # 3. Save to database using Repository
        save_result = await self.repo.bulk_upsert_leads(enriched_leads)
        
        logger.info(f"✅ Orchestration complete: {save_result}")

        # Construct response exactly as previously handled by the endpoint
        return {
            "success": True,
            "leads_found": len(leads),
            "message": f"Found {len(leads)} leads. Inserted: {save_result['inserted_count']}, Updated: {save_result['updated_count']}, Skipped: {save_result['skipped_count']}",
            "stats": {
                **search_result.get("stats", {}),
                "inserted_count": save_result["inserted_count"],
                "updated_count": save_result["updated_count"],
                "skipped_count": save_result["skipped_count"]
            }
        }

    async def refresh_lead_analysis(self, lead_id: int) -> Dict[str, Any]:
        """
        Re-runs AI analysis for a single lead using existing post data.
        """
        lead = await self.repo.get_by_id(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}

        post_data = safe_json_parse(lead.get("post_data"), default=[])

        if not post_data:
            return {"success": False, "error": "No post data available for refresh"}

        # Use the first post for analysis
        first_post = post_data[0] if isinstance(post_data, list) else post_data

        ai_result = await linkedin_intelligence_service.analyze_and_generate_dm(
            post_data=first_post,
            author_name=lead.get("full_name", ""),
            author_headline=lead.get("headline", "")
        )

        await self.repo.update_ai_enrichment(
            lead_id=lead_id,
            hiring_signal=ai_result.get("hiring_signal", False),
            hiring_roles=ai_result.get("hiring_roles", ""),
            pain_points=ai_result.get("pain_points", ""),
            ai_variables=ai_result.get("ai_variables", {}),
            linkedin_dm=ai_result.get("linkedin_dm", "")
        )

        return {
            "success": True,
            "ai_result": ai_result,
            "lead": lead
        }

    async def bulk_refresh_leads(self, lead_ids: List[int]) -> Dict[str, Any]:
        """
        Re-runs AI analysis for multiple leads.
        
        OPTIMIZED: Fetches all leads in a single query to avoid N+1 problem.
        """
        results = {"success_count": 0, "failed_count": 0, "errors": []}
        
        if not lead_ids:
            return results
        
        # OPTIMIZATION: Fetch all leads in ONE query instead of N queries
        logger.info(f"📦 Batch fetching {len(lead_ids)} leads...")
        leads = await self.repo.get_leads_by_ids(lead_ids)
        
        # Create a lookup map for quick access
        leads_map = {lead["id"]: lead for lead in leads}
        
        # Track which IDs were not found
        found_ids = set(leads_map.keys())
        missing_ids = set(lead_ids) - found_ids
        
        for missing_id in missing_ids:
            results["failed_count"] += 1
            results["errors"].append({"lead_id": missing_id, "error": "Lead not found"})
        
        # Process each found lead
        for lead_id in lead_ids:
            if lead_id not in leads_map:
                continue  # Already counted as missing
                
            lead = leads_map[lead_id]
            
            try:
                # Parse post_data
                post_data = safe_json_parse(lead.get("post_data"), default=[])
                
                if not post_data:
                    results["failed_count"] += 1
                    results["errors"].append({"lead_id": lead_id, "error": "No post data available"})
                    continue
                
                # Use the first post for analysis
                first_post = post_data[0] if isinstance(post_data, list) else post_data
                
                # Run AI analysis
                ai_result = await linkedin_intelligence_service.analyze_and_generate_dm(
                    post_data=first_post,
                    author_name=lead.get("full_name", ""),
                    author_headline=lead.get("headline", "")
                )
                
                # Update the lead in database
                await self.repo.update_ai_enrichment(
                    lead_id=lead_id,
                    hiring_signal=ai_result.get("hiring_signal", False),
                    hiring_roles=ai_result.get("hiring_roles", ""),
                    pain_points=ai_result.get("pain_points", ""),
                    ai_variables=ai_result.get("ai_variables", {}),
                    linkedin_dm=ai_result.get("linkedin_dm", "")
                )
                
                results["success_count"] += 1
                
            except Exception as e:
                logger.error(f"Bulk refresh failed for lead {lead_id}: {e}")
                results["failed_count"] += 1
                results["errors"].append({"lead_id": lead_id, "error": str(e)})
        
        logger.info(f"✅ Bulk refresh complete: {results['success_count']} success, {results['failed_count']} failed")
        return results
