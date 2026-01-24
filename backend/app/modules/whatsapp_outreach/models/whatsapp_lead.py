"""
WhatsApp Lead ORM Model
SQLAlchemy model representing the 'whatsapp_leads' table.

This table stores leads for WhatsApp outreach.
Source of truth is mobile_number (unique, not null).
Leads can be imported from email_outreach or linkedin_outreach modules.
"""
from sqlalchemy import Column, BigInteger, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.shared.db.base import Base


class WhatsAppLead(Base):
    """
    ORM Model for the whatsapp_leads table.
    
    Stores leads for WhatsApp DM outreach via WATI.
    Mobile number is the unique identifier (source of truth).
    """
    __tablename__ = "whatsapp_leads"

    # Primary Key
    id = Column(BigInteger, primary_key=True)
    
    # ============================================
    # CORE IDENTITY (mobile_number + first_name required)
    # ============================================
    mobile_number = Column(Text, unique=True, nullable=False)  # Source of truth, E.164 format
    first_name = Column(Text, nullable=False)                  # Required for personalization
    last_name = Column(Text, nullable=True)
    full_name = Column(Text, nullable=True)                    # Computed: first_name + last_name
    
    # ============================================
    # CONTACT INFO
    # ============================================
    email = Column(Text, nullable=True)                        # If available from other sources
    company_name = Column(Text, nullable=True)
    designation = Column(Text, nullable=True)
    linkedin_url = Column(Text, nullable=True)                 # Cross-reference
    sector = Column(Text, nullable=True)                       # Industry/sector
    
    # ============================================
    # LEAD SOURCE TRACKING
    # ============================================
    source = Column(Text, default='manual')                    # 'manual', 'email_import', 'linkedin_import'
    source_lead_id = Column(BigInteger, nullable=True)         # ID from original table if imported
    
    # ============================================
    # WHATSAPP SEND STATUS
    # ============================================
    is_wa_sent = Column(Boolean, default=False)                # Has any WhatsApp message been sent?
    last_sent_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp of last message
    last_template_used = Column(Text, nullable=True)           # Name of last template used
    last_delivery_status = Column(Text, nullable=True)         # PENDING/SENT/DELIVERED/READ/FAILED
    last_failed_reason = Column(Text, nullable=True)           # Error message if failed
    
    # ============================================
    # WATI INTEGRATION
    # ============================================
    wati_contact_id = Column(Text, nullable=True)              # WATI's internal contact ID
    wati_conversation_id = Column(Text, nullable=True)         # Current conversation thread ID
    
    # ============================================
    # TIMESTAMPS
    # ============================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ============================================
    # INDEXES
    # ============================================
    __table_args__ = (
        Index('idx_whatsapp_leads_mobile', 'mobile_number'),
        Index('idx_whatsapp_leads_source', 'source'),
        Index('idx_whatsapp_leads_sent', 'is_wa_sent'),
        Index('idx_whatsapp_leads_status', 'last_delivery_status'),
        Index('idx_whatsapp_leads_created', 'created_at'),
    )

    def __repr__(self):
        return f"<WhatsAppLead(id={self.id}, mobile='{self.mobile_number}', name='{self.first_name}'')>"
