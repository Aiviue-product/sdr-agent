"""
WhatsApp Activity Repository
Database operations for the whatsapp_activities table.

Handles both lead-specific and global activity logging.
"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.whatsapp_outreach.models.whatsapp_activity import WhatsAppActivity
from app.shared.core.constants import DEFAULT_PAGE_SIZE


class WhatsAppActivityRepository:
    """Repository for WhatsApp activity logging."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    # ============================================
    # READ OPERATIONS
    # ============================================
    
    async def get_activities_for_lead(
        self,
        lead_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[dict]:
        """
        Get activities for a specific lead.
        Ordered by created_at DESC (most recent first).
        """
        query = (
            select(WhatsAppActivity)
            .where(WhatsAppActivity.whatsapp_lead_id == lead_id)
            .order_by(WhatsAppActivity.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        activities = result.scalars().all()
        
        return [{k: v for k, v in a.__dict__.items() if not k.startswith('_')} for a in activities]
    
    async def get_global_activities(
        self,
        activity_type: Optional[str] = None,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE
    ) -> List[dict]:
        """
        Get global activities (is_global=True).
        Optionally filter by activity_type.
        """
        query = (
            select(WhatsAppActivity)
            .where(WhatsAppActivity.is_global == True)
        )
        
        if activity_type:
            query = query.where(WhatsAppActivity.activity_type == activity_type)
        
        query = query.order_by(WhatsAppActivity.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        activities = result.scalars().all()
        
        return [{k: v for k, v in a.__dict__.items() if not k.startswith('_')} for a in activities]
    
    async def get_all_activities(
        self,
        activity_type: Optional[str] = None,
        lead_id: Optional[int] = None,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE
    ) -> List[dict]:
        """
        Get all activities with optional filters.
        For activity modal/timeline.
        """
        query = select(WhatsAppActivity)
        
        if activity_type:
            query = query.where(WhatsAppActivity.activity_type == activity_type)
        
        if lead_id:
            query = query.where(WhatsAppActivity.whatsapp_lead_id == lead_id)
        
        query = query.order_by(WhatsAppActivity.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        activities = result.scalars().all()
        
        return [{k: v for k, v in a.__dict__.items() if not k.startswith('_')} for a in activities]
    
    async def get_total_count(
        self,
        activity_type: Optional[str] = None,
        lead_id: Optional[int] = None,
        global_only: bool = False
    ) -> int:
        """Get total count of activities for pagination."""
        query = select(func.count()).select_from(WhatsAppActivity)
        
        if activity_type:
            query = query.where(WhatsAppActivity.activity_type == activity_type)
        
        if lead_id:
            query = query.where(WhatsAppActivity.whatsapp_lead_id == lead_id)
        
        if global_only:
            query = query.where(WhatsAppActivity.is_global == True)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    # ============================================
    # CREATE OPERATIONS
    # ============================================
    
    async def create_activity(
        self,
        activity_type: str,
        title: str,
        lead_id: Optional[int] = None,
        description: Optional[str] = None,
        lead_name: Optional[str] = None,
        lead_mobile: Optional[str] = None,
        extra_data: Optional[dict] = None,
        is_global: bool = False
    ) -> dict:
        """
        Create a new activity record.
        
        Args:
            activity_type: Type of activity (message_sent, message_failed, reply_received, etc.)
            title: Human-readable title
            lead_id: Associated lead ID (optional for global-only activities)
            description: Additional details
            lead_name: Lead's name for quick display
            lead_mobile: Lead's mobile for reference
            extra_data: Additional metadata (template, status, etc.)
            is_global: Whether to show in global activity feed
        """
        activity = WhatsAppActivity(
            whatsapp_lead_id=lead_id,
            activity_type=activity_type,
            title=title,
            description=description,
            lead_name=lead_name,
            lead_mobile=lead_mobile,
            extra_data=extra_data or {},
            is_global=is_global
        )
        
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        
        return {k: v for k, v in activity.__dict__.items() if not k.startswith('_')}
    
    # ============================================
    # CONVENIENCE METHODS FOR COMMON ACTIVITIES
    # ============================================
    
    async def log_message_sent(
        self,
        lead_id: int,
        lead_name: str,
        lead_mobile: str,
        template_name: str,
        is_global: bool = True
    ) -> dict:
        """Log a message sent activity."""
        return await self.create_activity(
            activity_type="message_sent",
            title=f"WhatsApp sent to {lead_name}",
            lead_id=lead_id,
            description=f"Template: {template_name}",
            lead_name=lead_name,
            lead_mobile=lead_mobile,
            extra_data={"template_name": template_name},
            is_global=is_global
        )
    
    async def log_message_failed(
        self,
        lead_id: int,
        lead_name: str,
        lead_mobile: str,
        error: str,
        is_global: bool = True
    ) -> dict:
        """Log a message failed activity."""
        return await self.create_activity(
            activity_type="message_failed",
            title=f"WhatsApp failed for {lead_name}",
            lead_id=lead_id,
            description=error,
            lead_name=lead_name,
            lead_mobile=lead_mobile,
            extra_data={"error": error},
            is_global=is_global
        )
    
    async def log_message_delivered(
        self,
        lead_id: int,
        lead_name: str,
        lead_mobile: str,
        is_global: bool = False
    ) -> dict:
        """Log a message delivered activity."""
        return await self.create_activity(
            activity_type="message_delivered",
            title=f"Message delivered to {lead_name}",
            lead_id=lead_id,
            lead_name=lead_name,
            lead_mobile=lead_mobile,
            is_global=is_global
        )
    
    async def log_message_read(
        self,
        lead_id: int,
        lead_name: str,
        lead_mobile: str,
        is_global: bool = False
    ) -> dict:
        """Log a message read activity."""
        return await self.create_activity(
            activity_type="message_read",
            title=f"Message read by {lead_name}",
            lead_id=lead_id,
            lead_name=lead_name,
            lead_mobile=lead_mobile,
            is_global=is_global
        )
    
    async def log_reply_received(
        self,
        lead_id: int,
        lead_name: str,
        lead_mobile: str,
        reply_text: str,
        is_global: bool = True
    ) -> dict:
        """Log a reply received activity (important - always global)."""
        return await self.create_activity(
            activity_type="reply_received",
            title=f"Reply from {lead_name}",
            lead_id=lead_id,
            description=reply_text[:200] if reply_text else None,
            lead_name=lead_name,
            lead_mobile=lead_mobile,
            extra_data={"reply_text": reply_text},
            is_global=is_global
        )
    
    async def log_lead_created(
        self,
        lead_id: int,
        lead_name: str,
        lead_mobile: str,
        source: str = "manual",
        is_global: bool = False
    ) -> dict:
        """Log a lead created activity."""
        return await self.create_activity(
            activity_type="lead_created",
            title=f"Lead added: {lead_name}",
            lead_id=lead_id,
            description=f"Source: {source}",
            lead_name=lead_name,
            lead_mobile=lead_mobile,
            extra_data={"source": source},
            is_global=is_global
        )
    
    async def log_leads_imported(
        self,
        count: int,
        source: str,
        is_global: bool = True
    ) -> dict:
        """Log bulk leads import activity (global only)."""
        return await self.create_activity(
            activity_type="leads_imported",
            title=f"Imported {count} leads from {source}",
            description=f"Source: {source}",
            extra_data={"count": count, "source": source},
            is_global=is_global
        )
    
    async def log_bulk_send_started(
        self,
        lead_count: int,
        template_name: str,
        is_global: bool = True
    ) -> dict:
        """Log bulk send started activity."""
        return await self.create_activity(
            activity_type="bulk_send_started",
            title=f"Bulk send started: {lead_count} leads",
            description=f"Template: {template_name}",
            extra_data={"count": lead_count, "template_name": template_name},
            is_global=is_global
        )
    
    async def log_bulk_send_completed(
        self,
        success_count: int,
        failed_count: int,
        is_global: bool = True
    ) -> dict:
        """Log bulk send completed activity."""
        return await self.create_activity(
            activity_type="bulk_send_completed",
            title=f"Bulk send completed: {success_count} sent, {failed_count} failed",
            extra_data={"success_count": success_count, "failed_count": failed_count},
            is_global=is_global
        )
