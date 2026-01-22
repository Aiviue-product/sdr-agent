"""
LinkedIn Lead Repository
All database operations for the linkedin_outreach_leads table.

HYBRID APPROACH: One lead per person, but append new posts to post_data array.
"""
import json
from typing import Optional, List
from sqlalchemy import text, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.utils.json_utils import safe_json_parse
from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead
from app.shared.core.constants import DEFAULT_PAGE_SIZE


class LinkedInLeadRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ============================================
    # READ OPERATIONS
    # ============================================
    
    async def get_by_id(self, lead_id: int):
        """
        Fetch a single LinkedIn lead by ID.
        Returns all columns for detail view.
        """
        query = select(LinkedInLead).where(LinkedInLead.id == lead_id)
        result = await self.db.execute(query)
        lead = result.scalar_one_or_none()
        
        # Convert to dict for compatibility with existing code that expects mappings
        return lead.__dict__ if lead else None

    async def get_leads_by_ids(self, lead_ids: List[int]) -> List[dict]:
        """
        Fetch multiple LinkedIn leads by their IDs in a SINGLE query.
        This prevents N+1 query problems in bulk operations.
        
        Args:
            lead_ids: List of lead IDs to fetch
            
        Returns:
            List of lead dictionaries
        """
        if not lead_ids:
            return []
        
        query = select(LinkedInLead).where(LinkedInLead.id.in_(lead_ids))
        result = await self.db.execute(query)
        leads = result.scalars().all()
        
        # Convert to dicts for compatibility with service layer
        return [lead.__dict__ for lead in leads]

    async def get_all_leads(
        self, 
        keyword: Optional[str] = None, 
        skip: int = 0, 
        limit: int = DEFAULT_PAGE_SIZE
    ):
        """
        Fetch all LinkedIn leads with optional keyword filter.
        Used for the leads table display (cumulative view).
        
        Note: keyword filter checks if ANY post in post_data matches the keyword.
        """
        # Select specific columns (Partial selection) for efficiency
        query = select(
            LinkedInLead.id, 
            LinkedInLead.full_name, 
            LinkedInLead.first_name, 
            LinkedInLead.last_name, 
            LinkedInLead.company_name, 
            LinkedInLead.is_company,
            LinkedInLead.linkedin_url, 
            LinkedInLead.headline, 
            LinkedInLead.profile_image_url,
            LinkedInLead.search_keyword, 
            LinkedInLead.hiring_signal, 
            LinkedInLead.hiring_roles, 
            LinkedInLead.pain_points,
            LinkedInLead.is_dm_sent, 
            LinkedInLead.created_at, 
            LinkedInLead.post_data
        )

        if keyword:
            # Use JSONB contains (@>) operator for high-performance filtering
            # This looks for any post in the array that has this search_keyword
            query = query.where(LinkedInLead.post_data.contains([{"search_keyword": keyword}]))

        query = query.order_by(LinkedInLead.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        # Convert rows back to dict mappings for compatibility with existing code
        return [dict(row._mapping) for row in result.all()]

    async def get_total_count(self, keyword: Optional[str] = None) -> int:
        """
        Get total count of leads for pagination.
        Optionally filter by keyword.
        """
        query = select(func.count()).select_from(LinkedInLead)
        
        if keyword:
            # Consistent with get_all_leads filter
            query = query.where(LinkedInLead.post_data.contains([{"search_keyword": keyword}]))
        
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_unique_keywords(self) -> List[str]:
        """
        Get list of unique search keywords for filter dropdown.
        Extracts keywords from the post_data JSONB array.
        """
        query = text("""
            SELECT DISTINCT post->>'search_keyword' as keyword
            FROM linkedin_outreach_leads, 
                 jsonb_array_elements(post_data) AS post
            WHERE post->>'search_keyword' IS NOT NULL
            ORDER BY keyword
        """)
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall() if row[0]]

    async def get_existing_leads_by_urls(self, linkedin_urls: List[str]) -> dict:
        """
        Get existing leads by their LinkedIn URLs.
        Returns dict: {linkedin_url: lead_row}
        Used for hybrid upsert (to append posts to existing leads).
        """
        if not linkedin_urls:
            return {}
        
        # Only select needed columns for efficiency
        query = select(
            LinkedInLead.id, 
            LinkedInLead.linkedin_url, 
            LinkedInLead.post_data
        ).where(LinkedInLead.linkedin_url.in_(linkedin_urls))
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # Convert to dict lookup map: {url: {id, url, post_data}}
        return {
            row.linkedin_url: {
                "id": row.id, 
                "linkedin_url": row.linkedin_url, 
                "post_data": row.post_data
            } for row in rows
        }

    # ============================================
    # INSERT/UPSERT OPERATIONS (HYBRID APPROACH)
    # ============================================

    async def bulk_upsert_leads(self, leads: List[dict]) -> dict:
        """
        HYBRID UPSERT: Insert new leads OR append posts to existing leads.
        
        For NEW leads: Insert with post_data as array with one post
        For EXISTING leads: Append new post to post_data array
        
        Returns:
            dict with inserted_count, updated_count, and skipped_count
        """
        if not leads:
            return {"inserted_count": 0, "updated_count": 0, "skipped_count": 0}

        # Get all LinkedIn URLs from incoming leads
        urls = [lead["linkedin_url"] for lead in leads]
        
        # Find which leads already exist
        existing_leads = await self.get_existing_leads_by_urls(urls)
        
        new_leads = []
        leads_to_update = []
        skipped_count = 0
        
        for lead in leads:
            url = lead["linkedin_url"]
            
            if url in existing_leads:
                # Check if this exact post already exists (by post_url or activity_id)
                existing_record = existing_leads[url]
                existing_posts = existing_record.get("post_data") or []
                
                # Parse if it's a string
                existing_posts = safe_json_parse(existing_posts, default=[])
                
                # Check for duplicate post (same activity_id)
                new_post = lead.get("post_data", {})
                new_activity_id = new_post.get("activity_id") if isinstance(new_post, dict) else None
                
                already_has_post = any(
                    p.get("activity_id") == new_activity_id 
                    for p in existing_posts 
                    if isinstance(p, dict) and new_activity_id
                )
                
                if already_has_post:
                    skipped_count += 1
                else:
                    # Append this new post to existing lead
                    leads_to_update.append({
                        "id": existing_record["id"],
                        "new_post": new_post,
                        "search_keyword": lead.get("search_keyword")
                    })
            else:
                new_leads.append(lead)
        
        # Insert new leads
        inserted_count = 0
        if new_leads:
            inserted_count = await self._insert_new_leads(new_leads)
        
        # Update existing leads (append posts)
        updated_count = 0
        if leads_to_update:
            updated_count = await self._append_posts_to_existing(leads_to_update)
        
        return {
            "inserted_count": inserted_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count
        }

    async def _insert_new_leads(self, leads: List[dict]) -> int:
        """
        Insert brand new leads with their first post.
        post_data is stored as JSON array with single post.
        
        Uses INSERT ... ON CONFLICT for atomic upsert:
        - If lead is new: INSERT normally
        - If lead already exists (race condition): Append post to existing post_data
        
        TRANSACTION: All inserts happen atomically - if one fails, all are rolled back.
        """
        if not leads:
            return 0
            
        # Use ON CONFLICT for atomic upsert - handles race conditions
        query = text("""
            INSERT INTO linkedin_outreach_leads (
                full_name, first_name, last_name, company_name, is_company,
                linkedin_url, headline, profile_image_url,
                search_keyword, post_data,
                hiring_signal, hiring_roles, pain_points, ai_variables,
                linkedin_dm
            )
            VALUES (
                :full_name, :first_name, :last_name, :company_name, :is_company,
                :linkedin_url, :headline, :profile_image_url,
                :search_keyword, :post_data,
                :hiring_signal, :hiring_roles, :pain_points, :ai_variables,
                :linkedin_dm
            )
            ON CONFLICT (linkedin_url) DO UPDATE SET
                post_data = COALESCE(linkedin_outreach_leads.post_data, '[]'::jsonb) || excluded.post_data::jsonb,
                updated_at = NOW()
        """)

        # Use nested transaction (savepoint) for atomic bulk insert
        async with self.db.begin_nested():
            for lead in leads:
                # Wrap single post in array for consistency
                post_data = lead.get("post_data", {})
                if isinstance(post_data, dict):
                    # Add search_keyword to the post object for filtering
                    post_data["search_keyword"] = lead.get("search_keyword")
                    post_data_array = [post_data]
                else:
                    post_data_array = post_data if isinstance(post_data, list) else []
                
                params = {
                    "full_name": lead.get("full_name"),
                    "first_name": lead.get("first_name"),
                    "last_name": lead.get("last_name"),
                    "company_name": lead.get("company_name"),
                    "is_company": lead.get("is_company", False),
                    "linkedin_url": lead.get("linkedin_url"),
                    "headline": lead.get("headline"),
                    "profile_image_url": lead.get("profile_image_url"),
                    "search_keyword": lead.get("search_keyword"),
                    "post_data": json.dumps(post_data_array),
                    "hiring_signal": lead.get("hiring_signal", False),
                    "hiring_roles": lead.get("hiring_roles"),
                    "pain_points": lead.get("pain_points"),
                    "ai_variables": json.dumps(lead.get("ai_variables", {})),
                    "linkedin_dm": lead.get("linkedin_dm")
                }
                await self.db.execute(query, params)
        
        # Commit after successful nested transaction
        await self.db.commit()
        return len(leads)

    async def _append_posts_to_existing(self, updates: List[dict]) -> int:
        """
        Append new posts to existing leads' post_data array.
        Uses PostgreSQL JSONB concatenation.
        
        TRANSACTION: All updates happen atomically - if one fails, all are rolled back.
        """
        if not updates:
            return 0
            
        query = text("""
            UPDATE linkedin_outreach_leads 
            SET 
                post_data = COALESCE(post_data, '[]'::jsonb) || :new_post_json::jsonb,
                updated_at = NOW()
            WHERE id = :id
        """)

        # Use nested transaction (savepoint) for atomic bulk update
        async with self.db.begin_nested():
            for update in updates:
                new_post = update["new_post"]
                if isinstance(new_post, dict):
                    # Add search_keyword to the post
                    new_post["search_keyword"] = update.get("search_keyword")
                    # Wrap in array for JSONB array concatenation
                    new_post_json = json.dumps([new_post])
                else:
                    new_post_json = json.dumps([new_post])
                
                await self.db.execute(query, {
                    "id": update["id"],
                    "new_post_json": new_post_json
                })
        
        # Commit after successful nested transaction
        await self.db.commit()
        return len(updates)

    # ============================================
    # UPDATE OPERATIONS  
    # ============================================

    async def update_dm_sent(self, lead_id: int):
        """
        Mark a LinkedIn lead's DM as sent.
        """
        stmt = (
            update(LinkedInLead)
            .where(LinkedInLead.id == lead_id)
            .values(is_dm_sent=True, dm_sent_at=func.now())
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_connection_sent(self, lead_id: int):
        """
        Mark a LinkedIn lead's connection request as sent (pending).
        """
        stmt = (
            update(LinkedInLead)
            .where(LinkedInLead.id == lead_id)
            .values(
                connection_status="pending", 
                connection_sent_at=func.now(),
                updated_at=func.now()
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_ai_enrichment(
        self, 
        lead_id: int, 
        hiring_signal: bool,
        hiring_roles: str,
        pain_points: str,
        ai_variables: dict,
        linkedin_dm: str
    ):
        """
        Update AI enrichment data for a lead.
        Called after AI analysis is complete.
        """
        stmt = (
            update(LinkedInLead)
            .where(LinkedInLead.id == lead_id)
            .values(
                hiring_signal=hiring_signal,
                hiring_roles=hiring_roles,
                pain_points=pain_points,
                ai_variables=ai_variables, # SQLAlchemy JSONB handles dict -> json automatically
                linkedin_dm=linkedin_dm,
                updated_at=func.now()
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
