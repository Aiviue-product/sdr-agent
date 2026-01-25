"""
WhatsApp Message Repository
Database operations for the whatsapp_messages table.

Handles full conversation history tracking for each lead.
"""
from typing import Optional, List, Set
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.whatsapp_outreach.models.whatsapp_message import WhatsAppMessage
from app.shared.core.constants import DEFAULT_PAGE_SIZE


class WhatsAppMessageRepository:
    """Repository for WhatsApp message CRUD operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    # ============================================
    # READ OPERATIONS
    # ============================================
    
    async def get_by_id(self, message_id: int) -> Optional[dict]:
        """Fetch a single message by ID."""
        query = select(WhatsAppMessage).where(WhatsAppMessage.id == message_id)
        result = await self.db.execute(query)
        message = result.scalar_one_or_none()
        
        if message:
            return {k: v for k, v in message.__dict__.items() if not k.startswith('_')}
        return None
    
    async def get_by_wati_message_id(self, wati_message_id: str) -> Optional[dict]:
        """Fetch a message by WATI's message ID (for webhook matching)."""
        query = select(WhatsAppMessage).where(WhatsAppMessage.wati_message_id == wati_message_id)
        result = await self.db.execute(query)
        message = result.scalar_one_or_none()
        
        if message:
            return {k: v for k, v in message.__dict__.items() if not k.startswith('_')}
        return None
    
    async def get_messages_for_lead(
        self,
        lead_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[dict]:
        """
        Get conversation history for a lead.
        Ordered by created_at DESC (most recent first).
        """
        query = (
            select(WhatsAppMessage)
            .where(WhatsAppMessage.whatsapp_lead_id == lead_id)
            .order_by(WhatsAppMessage.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        return [{k: v for k, v in m.__dict__.items() if not k.startswith('_')} for m in messages]
    
    async def get_messages_count_for_lead(self, lead_id: int) -> int:
        """Get total message count for a lead."""
        query = (
            select(func.count())
            .select_from(WhatsAppMessage)
            .where(WhatsAppMessage.whatsapp_lead_id == lead_id)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def get_recent_messages(self, limit: int = 20) -> List[dict]:
        """Get recent messages across all leads (for global activity)."""
        query = (
            select(WhatsAppMessage)
            .order_by(WhatsAppMessage.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        return [{k: v for k, v in m.__dict__.items() if not k.startswith('_')} for m in messages]
    
    async def get_existing_wati_ids(self, lead_id: int) -> Set[str]:
        """Get all wati_message_ids for a lead to avoid duplicates."""
        query = select(WhatsAppMessage.wati_message_id).where(
            WhatsAppMessage.whatsapp_lead_id == lead_id,
            WhatsAppMessage.wati_message_id.isnot(None)
        )
        result = await self.db.execute(query)
        return {row[0] for row in result.all()}
    
    # ============================================
    # CREATE OPERATIONS
    # ============================================
    
    async def create_outbound_message(
        self,
        lead_id: int,
        template_name: str,
        message_text: str,
        parameters: dict = None,
        broadcast_name: str = None,
        wati_message_id: str = None,
        wati_conversation_id: str = None,
        status: str = "PENDING"
    ) -> dict:
        """
        Create a new outbound message record.
        Called when sending a template message via WATI.
        """
        message = WhatsAppMessage(
            whatsapp_lead_id=lead_id,
            direction="outbound",
            template_name=template_name,
            message_text=message_text,
            parameters=parameters or {},
            status=status,
            broadcast_name=broadcast_name,
            wati_message_id=wati_message_id,
            wati_conversation_id=wati_conversation_id,
            sent_at=func.now() if status in ["SENT", "DELIVERED", "READ"] else None
        )
        
        self.db.add(message)
        await self.db.flush()  # Flush to get ID, let service manage commit
        await self.db.refresh(message)
        
        return {k: v for k, v in message.__dict__.items() if not k.startswith('_')}
    
    async def create_inbound_message(
        self,
        lead_id: int,
        message_text: str,
        wati_message_id: str = None,
        wati_conversation_id: str = None
    ) -> dict:
        """
        Create a new inbound message record.
        Called when receiving a reply via webhook.
        """
        message = WhatsAppMessage(
            whatsapp_lead_id=lead_id,
            direction="inbound",
            template_name=None,
            message_text=message_text,
            parameters={},
            status="RECEIVED",
            wati_message_id=wati_message_id,
            wati_conversation_id=wati_conversation_id
        )
        
        self.db.add(message)
        await self.db.flush()  # Flush to get ID, let service manage commit
        await self.db.refresh(message)
        
        return {k: v for k, v in message.__dict__.items() if not k.startswith('_')}
    
    # ============================================
    # UPDATE OPERATIONS
    # ============================================
    
    async def update_status(
        self,
        message_id: int,
        status: str,
        failed_reason: str = None
    ):
        """Update message status."""
        update_values = {"status": status}
        
        if failed_reason:
            update_values["failed_reason"] = failed_reason
        
        # Set timestamp based on status
        if status == "SENT":
            update_values["sent_at"] = func.now()
        elif status == "DELIVERED":
            update_values["delivered_at"] = func.now()
        elif status == "READ":
            update_values["read_at"] = func.now()
        
        stmt = (
            update(WhatsAppMessage)
            .where(WhatsAppMessage.id == message_id)
            .values(**update_values)
        )
        
        await self.db.execute(stmt)
        # No commit - let service layer manage transaction
    
    async def update_status_by_wati_id(
        self,
        wati_message_id: str,
        status: str,
        failed_reason: str = None
    ) -> bool:
        """
        Update message status by WATI message ID.
        Used by webhook handler.
        Returns True if a message was updated.
        """
        update_values = {"status": status}
        
        if failed_reason:
            update_values["failed_reason"] = failed_reason
        
        if status == "SENT":
            update_values["sent_at"] = func.now()
        elif status == "DELIVERED":
            update_values["delivered_at"] = func.now()
        elif status == "READ":
            update_values["read_at"] = func.now()
        
        stmt = (
            update(WhatsAppMessage)
            .where(WhatsAppMessage.wati_message_id == wati_message_id)
            .values(**update_values)
        )
        
        result = await self.db.execute(stmt)
        # No commit - let service layer manage transaction
        
        return result.rowcount > 0
