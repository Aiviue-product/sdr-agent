"""
LinkedIn Lead Repository
All database operations for the linkedin_outreach_leads table.

HYBRID APPROACH: One lead per person, but append new posts to post_data array.
"""
import json
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
        query = text("SELECT * FROM linkedin_outreach_leads WHERE id = :id")
        result = await self.db.execute(query, {"id": lead_id})
        return result.mappings().first()

    async def get_all_leads(
        self, 
        keyword: Optional[str] = None, 
        skip: int = 0, 
        limit: int = 50
    ):
        """
        Fetch all LinkedIn leads with optional keyword filter.
        Used for the leads table display (cumulative view).
        
        Note: keyword filter checks if ANY post in post_data matches the keyword.
        """
        query_str = """
            SELECT 
                id, full_name, first_name, last_name, company_name, is_company,
                linkedin_url, headline, profile_image_url,
                search_keyword, hiring_signal, hiring_roles, pain_points,
                is_dm_sent, created_at, post_data
            FROM linkedin_outreach_leads 
            WHERE 1=1
        """
        params = {"limit": limit, "offset": skip}

        # Optional keyword filter - checks if keyword exists in post_data array
        if keyword:
            # Use JSONB contains to check if any post has this keyword
            query_str += """ AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(post_data) AS post 
                WHERE post->>'search_keyword' = :keyword
            )"""
            params["keyword"] = keyword

        query_str += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        result = await self.db.execute(text(query_str), params)
        return result.mappings().all()

    async def get_total_count(self, keyword: Optional[str] = None) -> int:
        """
        Get total count of leads for pagination.
        Optionally filter by keyword.
        """
        query_str = "SELECT COUNT(*) FROM linkedin_outreach_leads WHERE 1=1"
        params = {}
        
        if keyword:
            query_str += """ AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(post_data) AS post 
                WHERE post->>'search_keyword' = :keyword
            )"""
            params["keyword"] = keyword
        
        result = await self.db.execute(text(query_str), params)
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
        
        placeholders = ",".join([f":url_{i}" for i in range(len(linkedin_urls))])
        params = {f"url_{i}": url for i, url in enumerate(linkedin_urls)}
        
        query = text(f"""
            SELECT id, linkedin_url, post_data 
            FROM linkedin_outreach_leads 
            WHERE linkedin_url IN ({placeholders})
        """)
        result = await self.db.execute(query, params)
        
        return {row.linkedin_url: dict(row._mapping) for row in result.fetchall()}

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
                if isinstance(existing_posts, str):
                    existing_posts = json.loads(existing_posts)
                
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
        """
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
        """)

        try:
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
                    "search_keyword": lead.get("search_keyword"),  # First keyword that found them
                    "post_data": json.dumps(post_data_array),
                    "hiring_signal": lead.get("hiring_signal", False),
                    "hiring_roles": lead.get("hiring_roles"),
                    "pain_points": lead.get("pain_points"),
                    "ai_variables": json.dumps(lead.get("ai_variables", {})),
                    "linkedin_dm": lead.get("linkedin_dm")
                }
                await self.db.execute(query, params)
            
            await self.db.commit()
            return len(leads)
            
        except Exception as e:
            await self.db.rollback()
            raise e

    async def _append_posts_to_existing(self, updates: List[dict]) -> int:
        """
        Append new posts to existing leads' post_data array.
        Uses PostgreSQL JSONB concatenation.
        """
        query = text("""
            UPDATE linkedin_outreach_leads 
            SET 
                post_data = post_data || :new_post_json::jsonb,
                updated_at = NOW()
            WHERE id = :id
        """)

        try:
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
            
            await self.db.commit()
            return len(updates)
            
        except Exception as e:
            await self.db.rollback()
            raise e

    # ============================================
    # UPDATE OPERATIONS  
    # ============================================

    async def update_dm_sent(self, lead_id: int):
        """
        Mark a LinkedIn lead's DM as sent.
        (For future use when DM sending is implemented)
        """
        await self.db.execute(
            text("UPDATE linkedin_outreach_leads SET is_dm_sent = TRUE, dm_sent_at = NOW() WHERE id = :id"),
            {"id": lead_id}
        )
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
        await self.db.execute(
            text("""
                UPDATE linkedin_outreach_leads 
                SET 
                    hiring_signal = :hiring_signal,
                    hiring_roles = :hiring_roles,
                    pain_points = :pain_points,
                    ai_variables = :ai_variables,
                    linkedin_dm = :linkedin_dm,
                    updated_at = NOW()
                WHERE id = :id
            """),
            {
                "id": lead_id,
                "hiring_signal": hiring_signal,
                "hiring_roles": hiring_roles,
                "pain_points": pain_points,
                "ai_variables": json.dumps(ai_variables),
                "linkedin_dm": linkedin_dm
            }
        )
        await self.db.commit()
