"""
LinkedIn Outreach Lead ORM Model
SQLAlchemy model representing the 'linkedin_outreach_leads' table.

This table stores leads discovered via LinkedIn keyword search.
Leads come from posts matching hiring signals (e.g., "hiring for automobile").
"""
from sqlalchemy import Column, BigInteger, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.shared.db.base import Base


class LinkedInLead(Base):
    """
    ORM Model for the linkedin_outreach_leads table.
    
    Stores leads discovered via LinkedIn post keyword search.
    Each lead is a post author who shows hiring intent.
    """
    __tablename__ = "linkedin_outreach_leads"

    # Primary Key
    id = Column(BigInteger, primary_key=True)
    
    # ============================================
    # AUTHOR IDENTITY (from LinkedIn)
    # ============================================
    full_name = Column(Text, nullable=False)          # Complete name as-is from API
    first_name = Column(Text, nullable=True)          # First word of name (if person)
    last_name = Column(Text, nullable=True)           # Rest of name (if person)
    company_name = Column(Text, nullable=True)        # Company name (if company page)
    is_company = Column(Boolean, default=False)       # True if company page, else False
    
    # ============================================
    # LINKEDIN PROFILE INFO
    # ============================================
    linkedin_url = Column(Text, unique=True, nullable=False)  # Profile URL (dedup key)
    headline = Column(Text, nullable=True)            # Author headline from LinkedIn
    profile_image_url = Column(Text, nullable=True)   # Author image URL
    
    # ============================================
    # SEARCH CONTEXT
    # ============================================
    search_keyword = Column(Text, nullable=True)      # Which keyword found this lead
    post_data = Column(JSONB, nullable=True)          # Full original post object
    
    # ============================================
    # AI ENRICHMENT
    # ============================================
    hiring_signal = Column(Boolean, default=False)    # AI detected hiring intent
    hiring_roles = Column(Text, nullable=True)        # "CNC Supervisor, Field Manager"
    pain_points = Column(Text, nullable=True)         # AI-inferred challenges
    ai_variables = Column(JSONB, nullable=True, server_default='{}')  # Full AI analysis
    
    # ============================================
    # DM OUTREACH
    # ============================================
    linkedin_dm = Column(Text, nullable=True)         # AI-generated personalized DM
    is_dm_sent = Column(Boolean, default=False)       # Has DM been sent?
    dm_sent_at = Column(DateTime(timezone=True), nullable=True)  # When DM was sent
    
    # ============================================
    # TIMESTAMPS
    # ============================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ============================================
    # INDEXES
    # ============================================
    __table_args__ = (
        Index('idx_linkedin_leads_keyword', 'search_keyword'),
        Index('idx_linkedin_leads_hiring', 'hiring_signal'),
        Index('idx_linkedin_leads_dm_status', 'is_dm_sent'),
    )

    def __repr__(self):
        return f"<LinkedInLead(id={self.id}, name='{self.full_name}', company='{self.company_name}')>"
