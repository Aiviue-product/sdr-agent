"""
Lead Repository
All database operations for the leads table.
"""
import json
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.core.constants import DEFAULT_PAGE_SIZE


class LeadRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ============================================
    # READ OPERATIONS
    # ============================================
    
    async def get_by_id(self, lead_id: int):
        """
        Fetch a single lead by ID.
        Returns all columns.
        """
        query = text("SELECT * FROM leads WHERE id = :id")
        result = await self.db.execute(query, {"id": lead_id})
        return result.mappings().first()

    async def get_campaign_leads(self, sector: Optional[str] = None, skip: int = 0, limit: int = DEFAULT_PAGE_SIZE):
        """
        Fetch all verified leads for campaign view.
        Optionally filter by sector.
        """
        query_str = """
            SELECT 
                id, first_name, last_name, company_name, designation, sector, email, 
                verification_status, lead_stage, linkedin_url,
                hiring_signal, enrichment_status, ai_variables, is_sent
            FROM leads 
            WHERE verification_status = 'valid'
        """
        params = {"limit": limit, "offset": skip}

        if sector:
            query_str += " AND LOWER(sector) = LOWER(:sector)"
            params["sector"] = sector

        query_str += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        result = await self.db.execute(text(query_str), params)
        return result.mappings().all()

    async def get_incomplete_count(self):
        """
        Count leads with missing data (for frontend alert).
        """
        count_query = """
            SELECT COUNT(*) as incomplete_count
            FROM leads 
            WHERE verification_status = 'valid'
            AND (company_name IS NULL OR linkedin_url IS NULL OR mobile_number IS NULL 
                 OR designation IS NULL OR sector IS NULL)
        """
        result = await self.db.execute(text(count_query))
        return result.scalar() or 0

    async def get_enrichment_leads(self, sector: Optional[str] = None, skip: int = 0, limit: int = DEFAULT_PAGE_SIZE):
        """
        Fetch leads that have valid email but are missing some data.
        """
        query_str = """
            SELECT id, first_name, last_name, company_name, designation, sector, email, mobile_number, linkedin_url, lead_stage 
            FROM leads 
            WHERE verification_status = 'valid'
            AND (company_name IS NULL OR linkedin_url IS NULL OR mobile_number IS NULL 
                 OR designation IS NULL OR sector IS NULL)
        """
        params = {"limit": limit, "offset": skip}

        if sector:
            query_str += " AND LOWER(sector) = LOWER(:sector)"
            params["sector"] = sector

        query_str += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        result = await self.db.execute(text(query_str), params)
        return result.mappings().all()

    async def get_by_ids(self, lead_ids: List[int], columns: str = "*"):
        """
        Fetch multiple leads by their IDs.
        columns: Specify which columns to select (default: all)
        """
        if not lead_ids:
            return []
        
        placeholders = ",".join([f":id_{i}" for i in range(len(lead_ids))])
        params = {f"id_{i}": lid for i, lid in enumerate(lead_ids)}
        
        query = text(f"SELECT {columns} FROM leads WHERE id IN ({placeholders})")
        result = await self.db.execute(query, params)
        return result.mappings().all()

    async def get_by_ids_for_bulk_check(self, lead_ids: List[int]):
        """
        Fetch leads with specific columns for bulk eligibility check.
        """
        return await self.get_by_ids(
            lead_ids, 
            columns="id, email, linkedin_url, enrichment_status, ai_variables, is_sent, sector"
        )

    async def get_by_ids_for_bulk_push(self, lead_ids: List[int]):
        """
        Fetch leads with full data needed for Instantly bulk push.
        """
        return await self.get_by_ids(
            lead_ids,
            columns="""id, email, first_name, last_name, company_name, designation, sector,
                linkedin_url, personalized_intro,
                email_1_subject, email_1_body,
                email_2_subject, email_2_body,
                email_3_subject, email_3_body,
                enrichment_status, ai_variables, is_sent"""
        )

    async def get_verified_emails(self, email_list: List[str]) -> dict:
        """
        Check which emails from the list are already verified in the database.
        Returns a dict: { 'email@example.com': {'status': 'valid', 'tag': 'Verified'}, ... }
        
        This is used to prevent re-verification of already-verified leads,
        saving ZeroBounce API credits.
        """
        if not email_list:
            return {}
        
        # Clean and lowercase all emails for consistent matching
        clean_emails = [str(e).strip().lower() for e in email_list if e]
        
        if not clean_emails:
            return {}
        
        # Build parameterized query
        placeholders = ",".join([f":email_{i}" for i in range(len(clean_emails))])
        params = {f"email_{i}": email for i, email in enumerate(clean_emails)}
        
        query = text(f"""
            SELECT LOWER(email) as email, verification_status, verification_tag
            FROM leads 
            WHERE LOWER(email) IN ({placeholders})
            AND verification_status = 'valid'
        """)
        
        result = await self.db.execute(query, params)
        rows = result.mappings().all()
        
        # Build result dict
        verified_map = {}
        for row in rows:
            verified_map[row['email']] = {
                'status': row['verification_status'],
                'tag': row['verification_tag'] or 'Verified'
            }
        
        return verified_map

    # ============================================
    # UPDATE OPERATIONS
    # ============================================
    
    async def update_emails(self, lead_id: int, emails: dict):
        """
        Save generated email subjects and bodies for a lead.
        Used by fate_service after email generation.
        """
        update_query = text("""
            UPDATE leads 
            SET 
                email_1_subject = :s1, 
                email_1_body = :b1,
                email_2_subject = :s2, 
                email_2_body = :b2,
                email_3_subject = :s3, 
                email_3_body = :b3,
                updated_at = NOW()
            WHERE id = :id
        """)
        
        await self.db.execute(update_query, {
            "s1": emails["email_1"]["subject"], 
            "b1": emails["email_1"]["body"],
            "s2": emails["email_2"]["subject"], 
            "b2": emails["email_2"]["body"],
            "s3": emails["email_3"]["subject"], 
            "b3": emails["email_3"]["body"],
            "id": lead_id
        })
        await self.db.commit()

    async def update_enrichment_failed(self, lead_id: int):
        """
        Mark a lead's enrichment as failed.
        Called when scraping fails.
        """
        await self.db.execute(
            text("UPDATE leads SET enrichment_status = 'failed' WHERE id = :id"),
            {"id": lead_id}
        )
        await self.db.commit()

    async def update_enrichment_completed(self, lead_id: int, ai_analysis: dict, scraped_data: list):
        """
        Save enrichment results to a lead.
        Stores AI analysis, scraped data, and marks as completed.
        """
        await self.db.execute(
            text("""
                UPDATE leads 
                SET 
                    enrichment_status = 'completed',
                    hiring_signal = :hiring,
                    ai_variables = :ai_vars,
                    scraped_data = :scraped_json,
                    personalized_intro = :intro,
                    updated_at = NOW()
                WHERE id = :id
            """),
            {
                "id": lead_id,
                "hiring": ai_analysis.get("hiring_signal", False),
                "ai_vars": json.dumps(ai_analysis),
                "scraped_json": json.dumps(scraped_data),
                "intro": ai_analysis.get("summary_hook", "")
            }
        )
        await self.db.commit()

    async def update_sent_status(self, lead_id: int):
        """
        Mark a single lead as sent to Instantly.
        """
        await self.db.execute(
            text("UPDATE leads SET is_sent = TRUE, sent_at = NOW() WHERE id = :id"),
            {"id": lead_id}
        )
        await self.db.commit()

    async def bulk_update_sent(self, lead_ids: List[int]):
        """
        Mark multiple leads as sent to Instantly.
        """
        if not lead_ids:
            return
        
        placeholders = ",".join([f":id_{i}" for i in range(len(lead_ids))])
        params = {f"id_{i}": lid for i, lid in enumerate(lead_ids)}
        
        await self.db.execute(
            text(f"UPDATE leads SET is_sent = TRUE, sent_at = NOW() WHERE id IN ({placeholders})"),
            params
        )
        await self.db.commit()

    # ============================================
    # INSERT/UPSERT OPERATIONS
    # ============================================

    async def bulk_upsert_leads(self, leads: list, batch_size: int = 500):
        """
        Insert/update multiple leads in a batch (The Bus Approach).
        Handles large datasets (like 22k+ leads) by chunking them into batches
        to optimize performance and avoid memory/timeout issues.
        """ 
        if not leads:  
            return

        query = text("""
            INSERT INTO leads (
                email, first_name, last_name, company_name, linkedin_url, mobile_number, 
                designation, sector, priority, verification_status, verification_tag, lead_stage
            )
            VALUES (
                :email, :first_name, :last_name, :company_name, :linkedin_url, :mobile_number, 
                :designation, :sector, :priority, :verification_status, :verification_tag, :lead_stage
            )
            ON CONFLICT (email) 
            DO UPDATE SET 
                verification_status = EXCLUDED.verification_status,
                verification_tag = EXCLUDED.verification_tag,
                lead_stage = EXCLUDED.lead_stage,
                
                -- Smart Updates: Don't overwrite existing data with NULLs if new file is empty
                company_name = COALESCE(EXCLUDED.company_name, leads.company_name),
                linkedin_url = COALESCE(EXCLUDED.linkedin_url, leads.linkedin_url),
                mobile_number = COALESCE(EXCLUDED.mobile_number, leads.mobile_number),
                designation = COALESCE(EXCLUDED.designation, leads.designation),
                sector = COALESCE(EXCLUDED.sector, leads.sector),
                
                updated_at = NOW();
        """)

        # Process in chunks of 1000
        # Optimized Processing
        try:
            for i in range(0, len(leads), batch_size):
                batch = leads[i : i + batch_size]
                await self.db.execute(query, batch)
            
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback() # Important safety net!
            raise e
