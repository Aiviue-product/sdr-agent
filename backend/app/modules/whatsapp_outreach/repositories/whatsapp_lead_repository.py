"""
WhatsApp Lead Repository
Database operations for the whatsapp_leads table.

Key patterns:
- Upsert with COALESCE to preserve existing data
- Phone number normalization to E.164 format
- Batch operations with chunking
"""
import re
from typing import Optional, List, Dict
from sqlalchemy import text, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.modules.whatsapp_outreach.models.whatsapp_lead import WhatsAppLead
from app.shared.core.config import settings
from app.shared.core.constants import DEFAULT_PAGE_SIZE


class WhatsAppLeadRepository:
    """Repository for WhatsApp lead CRUD operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    # ============================================
    # PHONE NUMBER UTILITIES
    # ============================================
    
    @staticmethod
    def normalize_phone(phone: str, default_country_code: str = None) -> str:
        """
        Normalize phone number to E.164 format (country code + number).
        
        Examples:
            "9876543210" -> "919876543210" (with default 91)
            "+91 9876543210" -> "919876543210"
            "091-9876543210" -> "919876543210"
            "919876543210" -> "919876543210" (unchanged)
        """
        if not phone:
            return ""
        
        # Remove all non-digits
        cleaned = re.sub(r'\D', '', phone)
        
        # Remove leading zeros (country codes don't start with 0)
        cleaned = cleaned.lstrip('0')
        
        # If it's a 10-digit Indian number, add country code
        if len(cleaned) == 10:
            country_code = default_country_code or settings.WATI_DEFAULT_COUNTRY_CODE or "91"
            cleaned = country_code + cleaned
        
        return cleaned
    
    # ============================================
    # READ OPERATIONS
    # ============================================
    
    async def get_by_id(self, lead_id: int) -> Optional[dict]:
        """Fetch a single WhatsApp lead by ID."""
        query = select(WhatsAppLead).where(WhatsAppLead.id == lead_id)
        result = await self.db.execute(query)
        lead = result.scalar_one_or_none()
        
        if lead:
            # Convert to dict, excluding SQLAlchemy internals
            lead_dict = {k: v for k, v in lead.__dict__.items() if not k.startswith('_')}
            return lead_dict
        return None
    
    async def get_by_mobile(self, mobile_number: str) -> Optional[dict]:
        """Fetch a lead by mobile number."""
        normalized = self.normalize_phone(mobile_number)
        query = select(WhatsAppLead).where(WhatsAppLead.mobile_number == normalized)
        result = await self.db.execute(query)
        lead = result.scalar_one_or_none()
        
        if lead:
            lead_dict = {k: v for k, v in lead.__dict__.items() if not k.startswith('_')}
            return lead_dict
        return None
    
    async def get_all_leads(
        self,
        source: Optional[str] = None,
        is_sent: Optional[bool] = None,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE
    ) -> List[dict]:
        """
        Fetch all WhatsApp leads with optional filters.
        Returns list view columns (not full detail).
        """
        query = select(
            WhatsAppLead.id,
            WhatsAppLead.mobile_number,
            WhatsAppLead.first_name,
            WhatsAppLead.last_name,
            WhatsAppLead.full_name,
            WhatsAppLead.email,
            WhatsAppLead.company_name,
            WhatsAppLead.designation,
            WhatsAppLead.linkedin_url,
            WhatsAppLead.source,
            WhatsAppLead.is_wa_sent,
            WhatsAppLead.last_delivery_status,
            WhatsAppLead.last_sent_at,
            WhatsAppLead.created_at
        )
        
        if source:
            query = query.where(WhatsAppLead.source == source)
        
        if is_sent is not None:
            query = query.where(WhatsAppLead.is_wa_sent == is_sent)
        
        query = query.order_by(WhatsAppLead.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return [dict(row._mapping) for row in result.all()]
    
    async def get_total_count(
        self,
        source: Optional[str] = None,
        is_sent: Optional[bool] = None
    ) -> int:
        """Get total count of leads for pagination."""
        query = select(func.count()).select_from(WhatsAppLead)
        
        if source:
            query = query.where(WhatsAppLead.source == source)
        
        if is_sent is not None:
            query = query.where(WhatsAppLead.is_wa_sent == is_sent)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def get_leads_by_ids(self, lead_ids: List[int]) -> List[dict]:
        """Fetch multiple leads by IDs in single query."""
        if not lead_ids:
            return []
        
        query = select(WhatsAppLead).where(WhatsAppLead.id.in_(lead_ids))
        result = await self.db.execute(query)
        leads = result.scalars().all()
        
        return [{k: v for k, v in lead.__dict__.items() if not k.startswith('_')} for lead in leads]
    
    async def get_leads_not_sent(self, limit: int = 100) -> List[dict]:
        """Get leads that haven't been sent a WhatsApp message yet."""
        query = select(WhatsAppLead).where(
            WhatsAppLead.is_wa_sent == False
        ).order_by(WhatsAppLead.created_at.asc()).limit(limit)
        
        result = await self.db.execute(query)
        leads = result.scalars().all()
        
        return [{k: v for k, v in lead.__dict__.items() if not k.startswith('_')} for lead in leads]
    
    # ============================================
    # CREATE/UPSERT OPERATIONS
    # ============================================
    
    async def create_lead(self, lead_data: dict) -> dict:
        """
        Create a single lead with phone normalization.
        Returns created lead.
        """
        # Normalize phone
        lead_data["mobile_number"] = self.normalize_phone(lead_data.get("mobile_number", ""))
        
        # Compute full_name if not provided
        if not lead_data.get("full_name"):
            first = lead_data.get("first_name", "")
            last = lead_data.get("last_name", "")
            lead_data["full_name"] = f"{first} {last}".strip()
        
        lead = WhatsAppLead(**lead_data)
        self.db.add(lead)
        await self.db.flush()  # Flush to get ID, let service manage commit
        await self.db.refresh(lead)
        
        return {k: v for k, v in lead.__dict__.items() if not k.startswith('_')}
    
    async def upsert_lead(self, lead_data: dict) -> dict:
        """
        Insert or update a lead by mobile_number.
        Uses COALESCE to preserve existing values when new values are NULL.
        
        Returns:
            Created or updated lead dict with 'action' key ('inserted' or 'updated')
        """
        # Normalize phone
        mobile = self.normalize_phone(lead_data.get("mobile_number", ""))
        if not mobile:
            raise ValueError("mobile_number is required")
        
        lead_data["mobile_number"] = mobile
        
        # Compute full_name if not provided
        if not lead_data.get("full_name"):
            first = lead_data.get("first_name", "")
            last = lead_data.get("last_name", "")
            lead_data["full_name"] = f"{first} {last}".strip() if first or last else None
        
        # Build upsert query
        stmt = insert(WhatsAppLead).values(**lead_data)
        
        # On conflict, update with COALESCE
        update_dict = {}
        for key in ["first_name", "last_name", "full_name", "email", "company_name", 
                    "designation", "linkedin_url", "sector"]:
            if key in lead_data:
                update_dict[key] = func.coalesce(stmt.excluded[key], getattr(WhatsAppLead, key))
        
        # Always update source if provided (don't COALESCE)
        if "source" in lead_data:
            update_dict["source"] = lead_data["source"]
        if "source_lead_id" in lead_data:
            update_dict["source_lead_id"] = lead_data["source_lead_id"]
        
        update_dict["updated_at"] = func.now()
        
        stmt = stmt.on_conflict_do_update(
            index_elements=["mobile_number"],
            set_=update_dict
        ).returning(WhatsAppLead)
        
        result = await self.db.execute(stmt)
        # No commit here - let service layer manage transaction
        
        lead = result.scalar_one()
        lead_dict = {k: v for k, v in lead.__dict__.items() if not k.startswith('_')}
        
        return lead_dict
    
    async def bulk_upsert_leads(self, leads: List[dict], chunk_size: int = 500) -> Dict:
        """
        Bulk upsert leads with chunking for performance.
        
        OPTIMIZED: Uses batch lookup + single INSERT ON CONFLICT per chunk.
        Avoids N+1 queries by:
        1. Getting all existing mobiles in ONE query per chunk
        2. Using PostgreSQL INSERT ON CONFLICT for atomic upsert
        
        Returns:
            dict with inserted_count, updated_count, skipped_count, errors
        """
        if not leads:
            return {"inserted_count": 0, "updated_count": 0, "skipped_count": 0, "errors": []}
        
        results = {
            "inserted_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "errors": []
        }
        
        # Process in chunks
        for i in range(0, len(leads), chunk_size):
            chunk = leads[i:i + chunk_size]
            
            # Step 1: Normalize and validate all leads in chunk
            valid_leads = []
            normalized_mobiles = []
            
            for lead_data in chunk:
                try:
                    mobile = self.normalize_phone(lead_data.get("mobile_number", ""))
                    first_name = (lead_data.get("first_name") or "").strip()
                    
                    if not mobile:
                        results["skipped_count"] += 1
                        results["errors"].append(f"Missing mobile_number: {lead_data}")
                        continue
                    
                    if not first_name:
                        results["skipped_count"] += 1
                        results["errors"].append(f"Missing first_name for {mobile}")
                        continue
                    
                    # Prepare lead data
                    lead_data = lead_data.copy()  # Don't mutate original
                    lead_data["mobile_number"] = mobile
                    
                    # Compute full_name if not provided
                    if not lead_data.get("full_name"):
                        last = lead_data.get("last_name", "") or ""
                        lead_data["full_name"] = f"{first_name} {last}".strip()
                    
                    valid_leads.append(lead_data)
                    normalized_mobiles.append(mobile)
                    
                except Exception as e:
                    results["skipped_count"] += 1
                    results["errors"].append(f"Validation error: {str(e)}")
            
            if not valid_leads:
                continue
            
            # Step 2: Batch lookup existing leads (SINGLE QUERY for entire chunk)
            existing_query = select(WhatsAppLead.mobile_number).where(
                WhatsAppLead.mobile_number.in_(normalized_mobiles)
            )
            existing_result = await self.db.execute(existing_query)
            existing_mobiles = {row[0] for row in existing_result.all()}
            
            # Step 3: Process each lead with INSERT ON CONFLICT (atomic upsert)
            for lead_data in valid_leads:
                try:
                    mobile = lead_data["mobile_number"]
                    was_existing = mobile in existing_mobiles
                    
                    # Build upsert statement
                    stmt = insert(WhatsAppLead).values(**lead_data)
                    
                    # COALESCE for nullable fields
                    update_dict = {}
                    for key in ["first_name", "last_name", "full_name", "email", 
                                "company_name", "designation", "linkedin_url", "sector"]:
                        if key in lead_data and lead_data[key] is not None:
                            update_dict[key] = func.coalesce(
                                stmt.excluded[key], 
                                getattr(WhatsAppLead, key)
                            )
                    
                    # Always update source tracking
                    if "source" in lead_data:
                        update_dict["source"] = lead_data["source"]
                    if "source_lead_id" in lead_data:
                        update_dict["source_lead_id"] = lead_data["source_lead_id"]
                    
                    update_dict["updated_at"] = func.now()
                    
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["mobile_number"],
                        set_=update_dict
                    )
                    
                    await self.db.execute(stmt)
                    
                    if was_existing:
                        results["updated_count"] += 1
                    else:
                        results["inserted_count"] += 1
                        
                except Exception as e:
                    results["skipped_count"] += 1
                    results["errors"].append(f"Upsert error for {lead_data.get('mobile_number')}: {str(e)}")
            
            # Commit after each chunk
            await self.db.commit()
        
        return results
    
    # ============================================
    # UPDATE OPERATIONS
    # ============================================
    
    async def update_lead(self, lead_id: int, update_data: dict) -> Optional[dict]:
        """Update a lead's fields."""
        # Normalize phone if being updated
        if "mobile_number" in update_data:
            update_data["mobile_number"] = self.normalize_phone(update_data["mobile_number"])
        
        update_data["updated_at"] = func.now()
        
        stmt = (
            update(WhatsAppLead)
            .where(WhatsAppLead.id == lead_id)
            .values(**update_data)
            .returning(WhatsAppLead)
        )
        
        result = await self.db.execute(stmt)
        # No commit - let service layer manage transaction
        
        lead = result.scalar_one_or_none()
        if lead:
            return {k: v for k, v in lead.__dict__.items() if not k.startswith('_')}
        return None
    
    async def update_wa_sent_status(
        self,
        lead_id: int,
        status: str,
        template_name: str = None,
        failed_reason: str = None,
        wati_message_id: str = None,
        wati_conversation_id: str = None
    ):
        """
        Update WhatsApp send status for a lead.
        Called after sending a message via WATI.
        """
        update_values = {
            "is_wa_sent": True,
            "last_sent_at": func.now(),
            "last_delivery_status": status,
            "updated_at": func.now()
        }
        
        if template_name:
            update_values["last_template_used"] = template_name
        if failed_reason:
            update_values["last_failed_reason"] = failed_reason
        if wati_message_id:
            update_values["wati_contact_id"] = wati_message_id
        if wati_conversation_id:
            update_values["wati_conversation_id"] = wati_conversation_id
        
        stmt = (
            update(WhatsAppLead)
            .where(WhatsAppLead.id == lead_id)
            .values(**update_values)
        )
        
        await self.db.execute(stmt)
        # No commit - let service layer manage transaction
    
    async def update_delivery_status(self, lead_id: int, status: str, failed_reason: str = None):
        """Update delivery status from webhook."""
        update_values = {
            "last_delivery_status": status,
            "updated_at": func.now()
        }
        if failed_reason:
            update_values["last_failed_reason"] = failed_reason
        
        stmt = (
            update(WhatsAppLead)
            .where(WhatsAppLead.id == lead_id)
            .values(**update_values)
        )
        
        await self.db.execute(stmt)
        # No commit - let service layer manage transaction
    
    # ============================================
    # DELETE OPERATIONS
    # ============================================
    
    async def delete_lead(self, lead_id: int) -> bool:
        """Delete a lead by ID. Returns True if deleted."""
        result = await self.db.execute(
            text("DELETE FROM whatsapp_leads WHERE id = :id RETURNING id"),
            {"id": lead_id}
        )
        await self.db.commit()
        return result.rowcount > 0
