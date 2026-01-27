"""
WhatsApp Activity ORM Model
SQLAlchemy model representing the 'whatsapp_activities' table.

This table tracks all WhatsApp outreach activities for timeline display.
Supports both lead-specific activities and global activities.
Activity types: message_sent, message_failed, reply_received, status_updated, lead_imported, lead_created
"""
from sqlalchemy import Column, BigInteger, Text, Boolean, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.shared.db.base import Base


class WhatsAppActivity(Base):
    """
    ORM Model for the whatsapp_activities table.
    
    Tracks all WhatsApp outreach activities for timeline display.
    When lead_id is NULL and is_global=True, activity appears in global feed only.
    """
    __tablename__ = "whatsapp_activities"

    # Primary Key
    id = Column(BigInteger, primary_key=True)
    
    # ============================================
    # FOREIGN KEY (nullable for global activities)
    # ============================================
    whatsapp_lead_id = Column(
        BigInteger, 
        ForeignKey('whatsapp_leads.id', ondelete='CASCADE'), 
        nullable=True  # NULL = global-only activity
    )
    
    # ============================================
    # ACTIVITY DETAILS
    # ============================================
    activity_type = Column(Text, nullable=False)
    # Types: message_sent, message_failed, message_delivered, message_read,
    #        reply_received, lead_created, lead_imported, bulk_send_started,
    #        bulk_send_completed
    
    title = Column(Text, nullable=False)           # Human-readable title (e.g., "Message sent to Rahul")
    description = Column(Text, nullable=True)      # Additional details
    
    # ============================================
    # LEAD INFO (denormalized for quick display)
    # ============================================
    lead_name = Column(Text, nullable=True)        # Lead's name (for timeline display)
    lead_mobile = Column(Text, nullable=True)      # Lead's mobile (for reference)
    
    # ============================================
    # EXTRA METADATA
    # ============================================
    extra_data = Column(JSONB, nullable=True, server_default='{}')
    # Example extra_data: { "template_name": "test", "status": "DELIVERED", "message_id": "xyz" }
    
    # ============================================
    # GLOBAL VISIBILITY FLAG
    # ============================================
    is_global = Column(Boolean, default=False)     # True = shows in global activity feed
    
    # ============================================
    # TIMESTAMPS
    # ============================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ============================================
    # INDEXES
    # ============================================
    __table_args__ = (
        Index('idx_whatsapp_activities_lead_id', 'whatsapp_lead_id'),
        Index('idx_whatsapp_activities_type', 'activity_type'),
        Index('idx_whatsapp_activities_global', 'is_global'),
        Index('idx_whatsapp_activities_created', 'created_at'),
    )

    def __repr__(self):
        return f"<WhatsAppActivity(id={self.id}, type='{self.activity_type}', lead_id={self.whatsapp_lead_id})>"
