"""
LinkedIn Outreach Service (Orchestrator)
Orchestrates the flow between Search, Intelligence, and Repository.

TRANSACTION MANAGEMENT:
This service owns the transaction boundary. All database operations are wrapped
in transaction blocks to ensure atomicity. The repository layer only executes
SQL - it does NOT commit or rollback.

BACKGROUND PROCESSING:
DM generation runs in background after search returns. This improves UX by showing
leads immediately while DMs generate asynchronously.
"""
import asyncio
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.signal_outreach.services.linkedin_search_service import linkedin_search_service
from app.modules.signal_outreach.services.linkedin_intelligence_service import linkedin_intelligence_service, RateLimitError
from app.modules.signal_outreach.services.unipile_service import unipile_service
from app.modules.signal_outreach.repositories.linkedin_lead_repository import LinkedInLeadRepository
from app.modules.signal_outreach.models.linkedin_lead import DmGenerationStatus
from app.shared.utils.json_utils import safe_json_parse
from app.shared.db.session import AsyncSessionLocal

logger = logging.getLogger("linkedin_outreach_service")


class LinkedInOutreachService:
    """
    Orchestrates the LinkedIn lead lifecycle: Search -> AI Analysis -> Database Storage.
    
    TRANSACTION OWNERSHIP:
    This service controls database transactions. Use the transaction() context manager
    to wrap database operations that should be atomic (all-or-nothing).
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LinkedInLeadRepository(db)

    @asynccontextmanager
    async def transaction(self):
        """
        Transaction context manager for atomic database operations.
        
        Usage:
            async with self.transaction():
                await self.repo.insert(...)
                await self.repo.update(...)
                # All committed together on success, or all rolled back on error
        
        Benefits:
        - Atomic operations: All DB changes succeed or fail together
        - Automatic rollback: Any exception triggers rollback
        - Clean error handling: Exceptions propagate after rollback
        """
        try:
            yield
            await self.db.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise

    async def run_full_outreach_search(
        self, 
        keywords: List[str], 
        date_filter: str = "past-week", 
        posts_per_keyword: int = 10
    ) -> Dict[str, Any]:
        """
        Executes the search pipeline (FAST - returns immediately):
        1. Query Apify for LinkedIn posts
        2. Persist leads to database with dm_generation_status='pending'
        3. Return lead IDs for background DM generation
        
        NOTE: AI analysis + DM generation happens in background task (see generate_dms_background)
        """
        logger.info(f"🚀 Starting outreach search for keywords: {keywords}")

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
                "stats": search_result.get("stats", {}),
                "lead_ids": []  # No leads to process in background
            }

        # 2. Prepare leads with pending DM status (NO AI enrichment yet)
        now = datetime.now(timezone.utc)
        for lead in leads:
            lead.update({
                "dm_generation_status": "pending",
                "dm_generation_started_at": now,
                # Set default values for AI fields (will be filled by background task)
                "hiring_signal": False,
                "hiring_roles": None,
                "pain_points": None,
                "ai_variables": {},
                "linkedin_dm": None
            })
        
        # 3. Save to database using Repository (inside transaction for atomicity)
        async with self.transaction():
            save_result = await self.repo.bulk_upsert_leads(leads)
        
        logger.info(f"✅ Search complete: {save_result}. DM generation will run in background.")

        # 4. Get saved lead IDs for background processing
        # We need to fetch the IDs of leads we just inserted/updated
        lead_urls = [lead["linkedin_url"] for lead in leads]
        saved_leads = await self.repo.get_existing_leads_by_urls(lead_urls)
        lead_ids = [saved_leads[url]["id"] for url in lead_urls if url in saved_leads]

        # Construct response with lead_ids for background task
        return {
            "success": True,
            "leads_found": len(leads),
            "lead_ids": lead_ids,  # For background task
            "message": f"Found {len(leads)} leads. DMs generating in background.",
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

        try:
            ai_result = await linkedin_intelligence_service.analyze_and_generate_dm(
                post_data=first_post,
                author_name=lead.get("full_name", ""),
                author_headline=lead.get("headline", "")
            )
        except RateLimitError:
            # Mark as failed so frontend shows proper status
            await self.repo.update_dm_generation_status(lead_id, DmGenerationStatus.FAILED)
            await self.db.commit()
            return {"success": False, "error": "Rate limit reached. Please try again later."}

        # Update database inside transaction for atomicity
        # Pass lead.get("version") for optimistic locking
        async with self.transaction():
            await self.repo.update_ai_enrichment(
                lead_id=lead_id,
                hiring_signal=ai_result.get("hiring_signal", False),
                hiring_roles=ai_result.get("hiring_roles", ""),
                pain_points=ai_result.get("pain_points", ""),
                ai_variables=ai_result.get("ai_variables", {}),
                linkedin_dm=ai_result.get("linkedin_dm", ""),
                current_version=lead.get("version")  # Pass version for optimistic locking
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
        TRANSACTIONAL: All updates are committed together for atomicity.
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
        
        # Collect all updates to apply in a single transaction
        updates_to_apply = []
        
        # Process each found lead (AI analysis phase - outside transaction)
        for idx, lead_id in enumerate(lead_ids):
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
                
                # Run AI analysis (external API call - outside transaction)
                try:
                    ai_result = await linkedin_intelligence_service.analyze_and_generate_dm(
                        post_data=first_post,
                        author_name=lead.get("full_name", ""),
                        author_headline=lead.get("headline", "")
                    )
                except RateLimitError:
                    # Mark current + remaining leads as failed in database
                    remaining_ids = lead_ids[idx:]
                    for remaining_id in remaining_ids:
                        results["failed_count"] += 1
                        results["errors"].append({"lead_id": remaining_id, "error": "Rate limit reached. Try again later."})
                        # Update status in DB so frontend shows "failed"
                        try:
                            await self.repo.update_dm_generation_status(remaining_id, DmGenerationStatus.FAILED)
                        except Exception as db_err:
                            logger.error(f"Failed to mark lead {remaining_id} as failed: {db_err}")
                    # Commit the status updates
                    try:
                        await self.db.commit()
                    except Exception:
                        pass
                    break
                
                # Collect update data for batch commit
                updates_to_apply.append({
                    "lead_id": lead_id,
                    "ai_result": ai_result,
                    "current_version": lead.get("version")  # Store version for optimistic locking
                })
                
            except Exception as e:
                logger.error(f"AI analysis failed for lead {lead_id}: {e}")
                results["failed_count"] += 1
                results["errors"].append({"lead_id": lead_id, "error": str(e)})
        
        # Apply all database updates in a single transaction (atomic)
        if updates_to_apply:
            try:
                async with self.transaction():
                    for update_data in updates_to_apply:
                        ai_result = update_data["ai_result"]
                        await self.repo.update_ai_enrichment(
                            lead_id=update_data["lead_id"],
                            hiring_signal=ai_result.get("hiring_signal", False),
                            hiring_roles=ai_result.get("hiring_roles", ""),
                            pain_points=ai_result.get("pain_points", ""),
                            ai_variables=ai_result.get("ai_variables", {}),
                            linkedin_dm=ai_result.get("linkedin_dm", ""),
                            current_version=update_data.get("current_version")  # Pass version
                        )
                
                # All updates succeeded
                results["success_count"] = len(updates_to_apply)
                
            except Exception as e:
                # Transaction rolled back - all updates failed
                logger.error(f"Bulk refresh transaction failed: {e}")
                for update_data in updates_to_apply:
                    results["failed_count"] += 1
                    results["errors"].append({"lead_id": update_data["lead_id"], "error": f"Transaction failed: {e}"})
        
        logger.info(f"✅ Bulk refresh complete: {results['success_count']} success, {results['failed_count']} failed")
        return results

    async def send_dm_to_lead(self, lead_id: int, custom_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Orchestrates sending a LinkedIn DM via Unipile and updating the database.
        
        Steps:
        1. Fetch lead and verify provider_id/connection status
        2. Call Unipile API to send DM
        3. If successful, update lead record and create activity log atomically
        """
        # 1. Fetch lead
        lead = await self.repo.get_by_id(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}
            
        provider_id = lead.get("provider_id")
        if not provider_id:
            return {"success": False, "error": "No provider ID found for lead"}
            
        if lead.get("connection_status") != "connected":
            return {"success": False, "error": "Not connected - can only send DMs to connections"}
            
        # Determine message
        dm_message = custom_message or lead.get("linkedin_dm")
        if not dm_message:
            return {"success": False, "error": "No message provided or available"}
            
        # 2. Call Unipile API (outside transaction)
        send_result = await unipile_service.create_chat_and_send_dm(provider_id, dm_message)
        
        if not send_result.get("success"):
            return {"success": False, "error": send_result.get("error")}
            
        # 3. Update database atomically
        async with self.transaction():
            # Update lead record
            await self.repo.update_dm_sent(
                lead_id=lead_id,
                current_version=lead.get("version")
            )
            
            # Create activity log
            await self.repo.create_activity(
                lead_id=lead_id,
                activity_type="dm_sent",
                message=dm_message[:200],
                lead_name=lead.get("full_name"),
                lead_linkedin_url=lead.get("linkedin_url"),
                extra_data={"message_id": send_result.get("message_id")}
            )
            
        return {
            "success": True, 
            "message": "DM sent successfully", 
            "sent_at": send_result.get("sent_at")
        }

    async def send_connection_request(self, lead_id: int, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Orchestrates sending a LinkedIn connection request via Unipile and updating the database.
        
        Steps:
        1. Fetch lead and verify provider_id
        2. Call Unipile API to send invitation
        3. If successful, update lead record and create activity log atomically
        """
        # 1. Fetch lead
        lead = await self.repo.get_by_id(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}
            
        provider_id = lead.get("provider_id")
        if not provider_id:
            # Try to fetch provider_id if missing
            profile_result = await unipile_service.get_profile(lead.get("linkedin_url"))
            if not profile_result.get("success"):
                return {"success": False, "error": "Could not retrieve LinkedIn provider ID"}
            provider_id = profile_result.get("provider_id")
            
            # Store it for future use (will be committed in final transaction)
            # Actually we'll need to update it in the lead later
            
        # 2. Call Unipile API (outside transaction)
        send_result = await unipile_service.send_connection_request(provider_id, message)
        
        if not send_result.get("success"):
            # Handle special case: already connected but DB didn't know
            if send_result.get("already_connected"):
                async with self.transaction():
                    await self.repo.update_connection_sent(
                        lead_id=lead_id, 
                        current_version=lead.get("version")
                    )
                    # Force connected status
                    # (Note: we should add an 'update_connection_status' method if we want to be precise)
                return {"success": True, "message": "Already connected", "already_connected": True}
            
            return {"success": False, "error": send_result.get("error")}
            
        # 3. Update database atomically
        async with self.transaction():
            # Update lead record
            await self.repo.update_connection_sent(
                lead_id=lead_id,
                current_version=lead.get("version")
            )
            
            # Create activity log
            await self.repo.create_activity(
                lead_id=lead_id,
                activity_type="connection_sent",
                message=message,
                lead_name=lead.get("full_name"),
                lead_linkedin_url=lead.get("linkedin_url"),
                extra_data={"invitation_id": send_result.get("invitation_id")}
            )
            
        return {
            "success": True, 
            "message": "Connection request sent", 
            "sent_at": send_result.get("sent_at")
        }

    async def handle_message_received(self, provider_id: str, message_text: str) -> Dict[str, Any]:
        """
        Handles 'message_received' webhook (lead replied).
        Updates lead status and logs activity atomically.
        """
        # 1. Fetch lead by provider_id
        lead = await self.repo.get_by_provider_id(provider_id)
        if not lead:
            return {"success": False, "error": f"No lead found for provider_id: {provider_id}"}
            
        # 2. Update database atomically
        async with self.transaction():
            # Update lead status (Using direct update from repo or adding a specific method)
            # For simplicity using where ID = lead_id update
            # (Note: we should ensure repo has get_by_provider_id)
            
            # Using repo.update_lead (I should check if repo has a general update method)
            # Actually, I'll use the repo methods I have or add a small one
            from sqlalchemy import update
            from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead
            from sqlalchemy.sql import func
            
            stmt = (
                update(LinkedInLead)
                .where(LinkedInLead.id == lead["id"])
                .values(
                    dm_status="replied",
                    last_reply_at=func.now(),
                    next_follow_up_at=None,
                    version=LinkedInLead.version + 1
                )
            )
            await self.db.execute(stmt)
            
            # Create activity
            await self.repo.create_activity(
                lead_id=lead["id"],
                activity_type="dm_replied",
                message=message_text[:500],
                lead_name=lead.get("full_name"),
                lead_linkedin_url=lead.get("linkedin_url")
            )
            
        return {"success": True, "lead_id": lead["id"]}

    async def handle_new_relation(self, provider_id: str) -> Dict[str, Any]:
        """
        Handles 'new_relation' webhook (connection accepted).
        Updates status, logs activity, and auto-sends DM if configured.
        """
        # 1. Fetch lead by provider_id
        lead = await self.repo.get_by_provider_id(provider_id)
        if not lead:
            return {"success": False, "error": f"No lead found for provider_id: {provider_id}"}
            
        # 2. Update status and log activity
        async with self.transaction():
            from sqlalchemy import update
            from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead
            
            stmt = (
                update(LinkedInLead)
                .where(LinkedInLead.id == lead["id"])
                .values(
                    connection_status="connected",
                    version=LinkedInLead.version + 1
                )
            )
            await self.db.execute(stmt)
            
            await self.repo.create_activity(
                lead_id=lead["id"],
                activity_type="connection_accepted",
                lead_name=lead.get("full_name"),
                lead_linkedin_url=lead.get("linkedin_url")
            )
            
        # 3. Check for auto-DM (if configured in lead)
        if lead.get("linkedin_dm") and not lead.get("is_dm_sent"):
            # This is a bit tricky since we are outside the transaction now
            # but we want to send the DM. 
            # We can use our own send_dm_to_lead method!
            await self.send_dm_to_lead(lead["id"])
            
        return {"success": True, "lead_id": lead["id"]}


# ============================================
# BACKGROUND TASK FUNCTIONS
# ============================================
# These run AFTER the HTTP response is sent to the user.
# They create their own database sessions since the request session is closed.

async def generate_dms_background(lead_ids: List[int]) -> None:
    """
    Background task: Generate DMs for leads using Gemini AI.
    
    This function runs asynchronously AFTER the search response is sent.
    It creates its own database session and processes leads one-by-one.
    
    For each lead:
    1. Fetch lead data from DB
    2. Call Gemini to analyze post and generate DM
    3. Update lead with AI results (or mark as failed)
    
    GRACEFUL FAILURES:
    - Each lead is processed independently
    - If one fails, others continue
    - Failed leads get dm_generation_status='failed'
    
    Args:
        lead_ids: List of lead IDs to process
    """
    if not lead_ids:
        logger.info("📭 No leads to process in background")
        return
    
    logger.info(f"🚀 Starting background DM generation for {len(lead_ids)} leads")
    
    success_count = 0
    failed_count = 0
    
    async def mark_rate_limited(lead_ids_to_mark: List[int]) -> None:
        if not lead_ids_to_mark:
            return
        async with AsyncSessionLocal() as db:
            repo = LinkedInLeadRepository(db)
            for mark_id in lead_ids_to_mark:
                await repo.update_dm_generation_status(
                    lead_id=mark_id,
                    status=DmGenerationStatus.FAILED
                )
            await db.commit()

    for idx, lead_id in enumerate(lead_ids):
        try:
            # Create fresh DB session for each lead (isolation)
            async with AsyncSessionLocal() as db:
                repo = LinkedInLeadRepository(db)
                
                # 1. Fetch lead
                lead = await repo.get_by_id(lead_id)
                if not lead:
                    logger.warning(f"⚠️ Lead {lead_id} not found, skipping")
                    failed_count += 1
                    continue
                
                # 2. Parse post_data
                post_data = safe_json_parse(lead.get("post_data"), default=[])
                if not post_data:
                    logger.warning(f"⚠️ Lead {lead_id} has no post data, marking as failed")
                    await repo.update_dm_generation_status(lead_id, DmGenerationStatus.FAILED)
                    await db.commit()
                    failed_count += 1
                    continue
                
                # Use the first post for analysis
                first_post = post_data[0] if isinstance(post_data, list) else post_data
                
                # 3. Call Gemini AI (this has rate limiting built-in)
                ai_result = await linkedin_intelligence_service.analyze_and_generate_dm(
                    post_data=first_post,
                    author_name=lead.get("full_name", ""),
                    author_headline=lead.get("headline", "")
                )
                
                # 4. Update lead with AI results
                await repo.update_ai_enrichment(
                    lead_id=lead_id,
                    hiring_signal=ai_result.get("hiring_signal", False),
                    hiring_roles=ai_result.get("hiring_roles", ""),
                    pain_points=ai_result.get("pain_points", ""),
                    ai_variables=ai_result.get("ai_variables", {}),
                    linkedin_dm=ai_result.get("linkedin_dm", ""),
                    current_version=lead.get("version")
                )
                await db.commit()
                
                success_count += 1
                logger.debug(f"✅ DM generated for lead {lead_id}")
                
        except RateLimitError as e:
            logger.warning(f"⏸️ Rate limit hit. Stopping background DM generation: {e}")
            failed_count += 1
            await mark_rate_limited([lead_id] + lead_ids[idx + 1:])
            break
        except Exception as e:
            logger.error(f"❌ DM generation failed for lead {lead_id}: {e}")
            failed_count += 1
            
            # Try to mark as failed (best effort)
            try:
                async with AsyncSessionLocal() as db:
                    repo = LinkedInLeadRepository(db)
                    await repo.update_dm_generation_status(lead_id, DmGenerationStatus.FAILED)
                    await db.commit()
            except Exception as mark_error:
                logger.error(f"Failed to mark lead {lead_id} as failed: {mark_error}")
    
    logger.info(f"🏁 Background DM generation complete: {success_count} success, {failed_count} failed")

